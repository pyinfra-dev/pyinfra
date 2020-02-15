from __future__ import division, unicode_literals

from contextlib import contextmanager
from multiprocessing import cpu_count
from uuid import uuid4

import six

from gevent.pool import Pool
from pkg_resources import parse_version

from pyinfra import __version__, logger

from .config import Config
from .exceptions import PyinfraError
from .util import ensure_host_list, get_caller_frameinfo, sha1_hash

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

    initialised = False

    # A pyinfra.api.Inventory which stores all our pyinfra.api.Host's
    inventory = None

    # A pyinfra.api.Config
    config = None

    # Main gevent pool
    pool = None

    # Whether we are in an @operation (so inner ops aren't wrapped)
    in_op = False
    # Whether we are deploying (ie hosts are all ready)
    deploying = False

    # Current op hash for use w/facts
    current_op_hash = None

    loop_counter = None
    loop_line = None

    # Name of the current deploy
    in_deploy = False
    deploy_name = None
    deploy_kwargs = None
    deploy_data = None
    deploy_line_numbers = None

    # Flags for printing
    print_output = False  # print output from the actual deploy (-v)
    print_input = False

    print_fact_info = False  # log fact gathering as INFO > DEBUG (-v)
    print_fact_output = False  # print output from facts (-vv)
    print_fact_input = False

    # Used in CLI
    deploy_dir = None  # base directory for locating files/templates/etc
    current_op_file = 0  # increments for each file excuted to maintain order

    def __init__(self, inventory=None, config=None, **kwargs):
        if inventory:
            self.init(inventory, config, **kwargs)

    def init(self, inventory, config, initial_limit=None):
        # Config validation
        #

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
            # TODO: benchmark this
            # In my own tests the optimum number of parallel SSH processes is
            # ~20 per CPU core - no science here yet, needs benchmarking!
            cpus = cpu_count()
            ideal_parallel = cpus * 20

            config.PARALLEL = (
                min(ideal_parallel, len(inventory), MAX_PARALLEL)
                if MAX_PARALLEL is not None
                else min(ideal_parallel, len(inventory))
            )

        # If explicitly set, just issue a warning
        elif MAX_PARALLEL is not None and config.PARALLEL > MAX_PARALLEL:
            logger.warning((
                'Parallel set to {0}, but this may hit the open files limit of {1}.\n'
                '    Max recommended value: {2}'
            ).format(config.PARALLEL, nofile_limit, MAX_PARALLEL))

        # Actually initialise the state object
        #

        # Setup greenlet pools
        self.pool = Pool(config.PARALLEL)
        self.fact_pool = Pool(config.PARALLEL)

        # Connection storage
        self.ssh_connections = {}
        self.sftp_connections = {}

        # Private keys
        self.private_keys = {}

        # Facts storage
        self.facts = {}
        self.fact_locks = {}

        # Assign inventory/config
        self.inventory = inventory
        self.config = config

        # Hosts we've activated at any time
        self.activated_hosts = set()
        # Active hosts that *haven't* failed yet
        self.active_hosts = set()
        # Hosts that are ready to be deployed to
        self.ready_hosts = set()
        # Hosts that have failed
        self.failed_hosts = set()

        # Limit hosts changes dynamically to limit operations to a subset of hosts
        self.limit_hosts = initial_limit

        # Op basics
        self.op_line_numbers_to_hash = {}
        self.op_meta = {}  # maps operation hash -> names/etc
        self.ops_run = set()  # list of ops which have been started/run

        # Op dict for each host
        self.ops = {
            host: {}
            for host in inventory
        }

        # Facts dict for each host
        self.facts = {
            host: {}
            for host in inventory
        }

        # Meta dict for each host
        self.meta = {
            host: {
                'ops': 0,  # one function call in a deploy file
                'commands': 0,  # actual # of commands to run
                'op_hashes': set(),
            }
            for host in inventory
        }

        # Results dict for each host
        self.results = {
            host: {
                'ops': 0,  # success_ops + failed ops w/ignore_errors
                'success_ops': 0,
                'error_ops': 0,
                'commands': 0,
            }
            for host in inventory
        }

        # Assign state back references to inventory & config
        inventory.state = config.state = self

        self.initialised = True

    def limit(self, hosts):
        logger.warning((
            'Use of `State.limit` is deprecated, '
            'please use normal `if` statements instead.'
        ))

        return self.hosts(hosts)

    @contextmanager
    def hosts(self, hosts):
        logger.warning((
            'Use of `State.hosts` is deprecated, '
            'please use normal `if` statements instead.'
        ))

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
        logger.warning((
            'Use of `State.when` is deprecated, '
            'please use normal `if` statements instead.'
        ))

        # Truth-y? Just yield/end, nothing happens here!
        if predicate:
            yield
            return

        # Otherwise limit any operations within to match no hosts
        with self.hosts([]):
            yield

    @contextmanager
    def deploy(self, name, kwargs, data, line_number, in_deploy=True):
        '''
        Wraps a group of operations as a deploy, this should not be used
        directly, instead use ``pyinfra.api.deploy.deploy``.
        '''

        # Handle nested deploy names
        if self.deploy_name:
            name = _make_name(self.deploy_name, name)

        # Store the previous values
        old_in_deploy = self.in_deploy
        old_deploy_name = self.deploy_name
        old_deploy_kwargs = self.deploy_kwargs
        old_deploy_data = self.deploy_data
        old_deploy_line_numbers = self.deploy_line_numbers
        self.in_deploy = in_deploy

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

        # Make new line numbers - note convert from and back to tuple to avoid
        # keeping deploy_line_numbers mutable.
        new_line_numbers = list(self.deploy_line_numbers or [])
        new_line_numbers.append(line_number)
        new_line_numbers = tuple(new_line_numbers)

        # Set the new values
        self.deploy_name = name
        self.deploy_kwargs = kwargs
        self.deploy_data = data
        self.deploy_line_numbers = new_line_numbers
        logger.debug('Starting deploy {0} (args={1}, data={2})'.format(
            name, kwargs, data,
        ))

        yield

        # Restore the previous values
        self.in_deploy = old_in_deploy
        self.deploy_name = old_deploy_name
        self.deploy_kwargs = old_deploy_kwargs
        self.deploy_data = old_deploy_data
        self.deploy_line_numbers = old_deploy_line_numbers

        logger.debug('Reset deploy to {0} (args={1}, data={2})'.format(
            old_deploy_name, old_deploy_kwargs, old_deploy_data,
        ))

    @contextmanager
    def preserve_loop_order(self, items):
        frameinfo = get_caller_frameinfo(frame_offset=1)  # escape contextlib
        self.loop_line = frameinfo.lineno

        def item_generator():
            for i, item in enumerate(items, 1):
                self.loop_counter = i
                yield item

        yield item_generator

        self.loop_counter = None
        self.loop_line = None

    def get_op_order(self):
        line_numbers_to_hash = self.op_line_numbers_to_hash
        sorted_line_numbers = sorted(list(line_numbers_to_hash.keys()))

        return [
            line_numbers_to_hash[numbers]
            for numbers in sorted_line_numbers
        ]

    def activate_host(self, host):
        '''
        Flag a host as active.
        '''

        logger.debug('Activating host: {0}'.format(host))

        # Add to *both* activated and active - active will reduce as hosts fail
        # but connected will not, enabling us to track failed %.
        self.activated_hosts.add(host)
        self.active_hosts.add(host)

    # def ready_host(self, host):
    #     '''
    #     Flag a host as ready, after which facts will not be gathered for it.
    #     '''

    #     logger.debug('Readying host: {0}'.format(host))
    #     self.ready_hosts.add(host)

    def fail_hosts(self, hosts_to_fail, activated_count=None):
        '''
        Flag a ``set`` of hosts as failed, error for ``config.FAIL_PERCENT``.
        '''

        if not hosts_to_fail:
            return

        activated_count = activated_count or len(self.activated_hosts)

        logger.debug('Failing hosts: {0}'.format(', '.join(
            (host.name for host in hosts_to_fail),
        )))

        self.failed_hosts.update(hosts_to_fail)

        self.active_hosts -= hosts_to_fail

        # Check we're not above the fail percent
        active_hosts = self.active_hosts

        # No hosts left!
        if not active_hosts:
            raise PyinfraError('No hosts remaining!')

        if self.config.FAIL_PERCENT is not None:
            percent_failed = (
                1 - len(active_hosts) / activated_count
            ) * 100

            if percent_failed > self.config.FAIL_PERCENT:
                raise PyinfraError('Over {0}% of hosts failed ({1}%)'.format(
                    self.config.FAIL_PERCENT,
                    int(round(percent_failed)),
                ))

    def is_host_in_limit(self, host):
        '''
        Returns a boolean indicating if the host is within the current state limit.
        '''

        limit_hosts = self.limit_hosts

        if not isinstance(limit_hosts, list):
            return True
        return host in limit_hosts

    def get_temp_filename(self, hash_key=None):
        '''
        Generate a temporary filename for this deploy.
        '''

        if not hash_key:
            hash_key = six.text_type(uuid4())

        temp_filename = '{0}/{1}'.format(
            self.config.TEMP_DIR, sha1_hash(hash_key),
        )

        return temp_filename
