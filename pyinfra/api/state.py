# pyinfra
# File: pyinfra/api/state.py
# Desc: class that represents the current pyinfra.state

from __future__ import division, unicode_literals

from uuid import uuid4

import six

from gevent.pool import Pool
from pkg_resources import parse_version

from pyinfra import logger, __version__

from .config import Config
from .util import sha1_hash
from .exceptions import PyinfraError
from .pipelining import PipelineFacts

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

    # Current op args tuple (sudo, sudo_user, ignore_errors) for use w/facts
    current_op_meta = None

    # Flag for pipelining mode
    pipelining = False

    # List of hosts to only apply operations to
    limit_hosts = None

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
                six.text_type(config.MIN_PYINFRA_VERSION)
            )

            if needed_version > running_version:
                raise PyinfraError((
                    'Minimum version not met '
                    '(minimum={0}, running={1})'
                ).format(
                    config.MIN_PYINFRA_VERSION,
                    __version__
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
        self.active_hosts = set()
        self.ready_hosts = set()
        self.connected_hosts = set()

        hostnames = [host.name for host in inventory]

        # Op basics
        self.op_order = []  # list of operation hashes
        self.op_meta = {}  # maps operation hash -> names/etc
        self.ops_run = set()  # list of ops which have been started/run

        # Op dict for each host
        self.ops = {
            hostname: {}
            for hostname in hostnames
        }

        # Meta dict for each host
        self.meta = {
            hostname: {
                'ops': 0,  # one function call in a deploy file
                'commands': 0,  # actual # of commands to run
                'latest_op_hash': None
            }
            for hostname in hostnames
        }

        # Results dict for each host
        self.results = {
            hostname: {
                'ops': 0,  # success_ops + failed ops w/ignore_errors
                'success_ops': 0,
                'error_ops': 0,
                'commands': 0
            }
            for hostname in hostnames
        }

        # Pipeline facts context manager attached to self
        self.pipeline_facts = PipelineFacts(self)

    def ready_host(self, host):
        '''
        Flag a host as ready, after which facts will not be gathered for it.
        '''

        self.ready_hosts.add(host)

    def fail_hosts(self, hosts_to_fail):
        '''
        Flag a ``set`` of hosts as failed, error for ``config.FAIL_PERCENT``.
        '''

        # Remove the failed hosts from the inventory
        self.active_hosts -= hosts_to_fail

        # Check we're not above the fail percent
        active_hosts = self.active_hosts

        # No hosts left!
        if not active_hosts:
            raise PyinfraError('No hosts remaining!')

        if self.config.FAIL_PERCENT is not None:
            percent_failed = (1 - len(active_hosts) / len(self.inventory)) * 100
            if percent_failed > self.config.FAIL_PERCENT:
                raise PyinfraError('Over {0}% of hosts failed'.format(
                    self.config.FAIL_PERCENT
                ))

    def get_temp_filename(self, hash_key=None):
        '''
        Generate a temporary filename for this deploy.
        '''

        if not hash_key:
            hash_key = six.text_type(uuid4())

        temp_filename = sha1_hash(hash_key)
        return '{0}/{1}'.format(self.config.TEMP_DIR, temp_filename)
