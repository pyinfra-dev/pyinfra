# pyinfra
# File: pyinfra/api/state.py
# Desc: class that represents the current pyinfra.state

from __future__ import division, unicode_literals

from contextlib import contextmanager
from uuid import uuid4

import six

from gevent.pool import Pool
from pkg_resources import parse_version

from pyinfra import __version__, logger

from .config import Config
from .exceptions import PyinfraError
from .util import ensure_host_list, sha1_hash

# Work out the max parallel we can achieve with the open files limit of the user/process,
# take 10 for opening Python files and /3 for ~3 files per host during op runs.
# See: https://github.com/Fizzadar/pyinfra/issues/44
try:
    from resource import getrlimit, RLIMIT_NOFILE
    nofile_limit, _ = getrlimit(RLIMIT_NOFILE)
    MAX_PARALLEL = round((nofile_limit - 10) / 3)

# Resource isn't available on Windows
except ImportError:
    nofile_limit = 0
    MAX_PARALLEL = None


def _make_name(current, new):
    '''
    Stops duplication between similarly named nested deploys, eg:

    Turn:
        Deploy Kubernetes master/Configure Kubernetes
    Into:
        Deploy Kubernetes master/Configure
    '''

    current_tokens = current.split()
    new_tokens = new.split()

    new = ' '.join(
        new_token for new_token in new_tokens
        if new_token not in current_tokens
    )

    return '/'.join((current, new))


class State(object):
    '''
    Manages state for a pyinfra deploy.
    '''

    # A pyinfra.api.Inventory which stores all our pyinfra.api.Host's
    inventory = None

    # A pyinfra.api.Config
    config = None

    # Main gevent pool
    pool = None

    # Whether we are in an @operation (so inner ops aren't wrapped)
    in_op = False

    # Current op hash for use w/facts
    current_op_hash = None

    # List of hosts to only apply operations to
    limit_hosts = None

    # Name of the current deploy
    in_deploy = False
    deploy_name = None
    deploy_kwargs = None
    deploy_data = None

    # Flags for printing
    print_output = False  # print output from the actual deploy (-v)
    print_fact_info = False  # log fact gathering as INFO > DEBUG (-v)
    print_fact_output = False  # print output from facts (-vv)
    print_lines = False  # print blank lines between operations (always in CLI)

    # Used in CLI
    deploy_dir = None  # base directory for locating files/templates/etc
    active = True  # used to disable operation calls when scanning deploy.py for config
    is_cli = False

    def __init__(self, inventory, config=None):
        # Connection storage
        self.ssh_connections = {}
        self.sftp_connections = {}

        # Private keys
        self.private_keys = {}

        # Facts storage
        self.facts = {}
        self.fact_locks = {}

        # If no config, create one using the defaults
        if config is None:
            config = Config()

        # Error if our min version is not met
        if config.MIN_PYINFRA_VERSION is not None:
            running_version = parse_version(__version__)
            needed_version = parse_version(
                # Version must be a string
                six.text_type(config.MIN_PYINFRA_VERSION),
            )

            if needed_version > running_version:
                raise PyinfraError((
                    'Minimum pyinfra version not met '
                    '(minimum={0}, running={1})'
                ).format(
                    config.MIN_PYINFRA_VERSION,
                    __version__,
                ))

        if not config.PARALLEL:
            # If possible run everything in parallel, otherwise the max if defined above
            config.PARALLEL = (
                min(len(inventory), MAX_PARALLEL)
                if MAX_PARALLEL is not None
                else len(inventory)
            )

        # If explicitly set, just issue a warning
        elif MAX_PARALLEL is not None and config.PARALLEL > MAX_PARALLEL:
            logger.warning((
                'Parallel set to {0}, but this may hit the open files limit of {1}.\n'
                '    Max recommended value: {2}'
            ).format(config.PARALLEL, nofile_limit, MAX_PARALLEL))

        # Setup greenlet pools
        self.pool = Pool(config.PARALLEL)
        self.fact_pool = Pool(config.PARALLEL)

        # Assign inventory/config
        self.inventory = inventory
        self.config = config

        # Assign self to inventory & config
        inventory.state = config.state = self

        # Host tracking
        self.connected_host_names = set()  # host names we managed to connect to
        self.ready_host_names = set()  # host names ready to be deployed to
        self.active_host_names = set()  # host names that haven't failed (yet!)

        host_names = [host.name for host in inventory]

        # Op basics
        self.op_order = []  # list of operation hashes
        self.op_meta = {}  # maps operation hash -> names/etc
        self.ops_run = set()  # list of ops which have been started/run

        # Op dict for each host
        self.ops = {
            name: {}
            for name in host_names
        }

        # Facts dict for each host
        self.facts = {
            name: {}
            for name in host_names
        }

        # Meta dict for each host
        self.meta = {
            name: {
                'ops': 0,  # one function call in a deploy file
                'commands': 0,  # actual # of commands to run
                'latest_op_hash': None,
            }
            for name in host_names
        }

        # Results dict for each host
        self.results = {
            name: {
                'ops': 0,  # success_ops + failed ops w/ignore_errors
                'success_ops': 0,
                'error_ops': 0,
                'commands': 0,
            }
            for name in host_names
        }

    @contextmanager
    def limit(self, hosts):
        hosts = ensure_host_list(hosts, inventory=self.inventory)

        # Store the previous value
        old_limit_hosts = self.limit_hosts

        # Limit the new hosts to a subset of the old hosts if they existed
        if old_limit_hosts is not None:
            hosts = [
                host for host in hosts
                if host in old_limit_hosts
            ]

        # Set the new value
        self.limit_hosts = hosts
        logger.debug('Setting limit to hosts: {0}'.format(hosts))

        yield

        # Restore the old value
        self.limit_hosts = old_limit_hosts
        logger.debug('Reset limit to hosts: {0}'.format(old_limit_hosts))

    @contextmanager
    def when(self, predicate):
        # Truth-y? Just yield/end, nothing happens here!
        if predicate:
            yield
            return

        # Otherwise limit any operations within to match no hosts
        with self.limit([]):
            yield

    @contextmanager
    def deploy(self, name, kwargs, data):
        '''
        Wraps a group of operations as a deploy, this should not be used directly,
        instead use ``pyinfra.api.deploy.deploy``.
        '''

        # Handle nested deploy names
        if self.deploy_name:
            name = _make_name(self.deploy_name, name)

        self.in_deploy = True

        # Store the previous values
        old_deploy_name = self.deploy_name
        old_deploy_kwargs = self.deploy_kwargs
        old_deploy_data = self.deploy_data

        # Limit the new hosts to a subset of the old hosts if they existed
        if (
            old_deploy_kwargs
            and old_deploy_kwargs.get('hosts') is not None
        ):
            # If we have hosts - subset them based on the old hosts
            if 'hosts' in kwargs:
                kwargs['hosts'] = [
                    host for host in kwargs['hosts']
                    if host in old_deploy_kwargs['hosts']
                ]
            # Otherwise simply carry the previous hosts
            else:
                kwargs['hosts'] = old_deploy_kwargs['hosts']

        # Set the new values
        self.deploy_name = name
        self.deploy_kwargs = kwargs
        self.deploy_data = data
        logger.debug('Starting deploy {0} (args={1}, data={2})'.format(
            name, kwargs, data,
        ))

        yield

        # Restore the previous values
        self.deploy_name = old_deploy_name
        self.deploy_kwargs = old_deploy_kwargs
        self.deploy_data = old_deploy_data
        logger.debug('Reset deploy to {0} (args={1}, data={2})'.format(
            old_deploy_name, old_deploy_kwargs, old_deploy_data,
        ))

        self.in_deploy = False

    def ready_host(self, host):
        '''
        Flag a host as ready, after which facts will not be gathered for it.
        '''

        self.ready_host_names.add(host)

    def fail_hosts(self, hosts_to_fail):
        '''
        Flag a ``set`` of hosts as failed, error for ``config.FAIL_PERCENT``.
        '''

        # Remove the failed hosts from the inventory
        self.active_host_names -= hosts_to_fail

        # Check we're not above the fail percent
        active_host_names = self.active_host_names

        # No hosts left!
        if not active_host_names:
            raise PyinfraError('No hosts remaining!')

        if self.config.FAIL_PERCENT is not None:
            percent_failed = (
                1 - len(active_host_names) / self.inventory.len_all_hosts()
            ) * 100

            if percent_failed > self.config.FAIL_PERCENT:
                raise PyinfraError('Over {0}% of hosts failed'.format(
                    self.config.FAIL_PERCENT,
                ))

    def get_temp_filename(self, hash_key=None):
        '''
        Generate a temporary filename for this deploy.
        '''

        if not hash_key:
            hash_key = six.text_type(uuid4())

        temp_filename = sha1_hash(hash_key)
        return '{0}/{1}'.format(self.config.TEMP_DIR, temp_filename)
