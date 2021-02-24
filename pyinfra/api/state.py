from __future__ import division, unicode_literals

from contextlib import contextmanager
from multiprocessing import cpu_count
from os import path
from uuid import uuid4

import six

from gevent.pool import Pool
from pkg_resources import parse_version, require, Requirement, ResolutionError

from pyinfra import __version__, logger

from .config import Config
from .exceptions import PyinfraError
from .util import get_caller_frameinfo, sha1_hash

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


class BaseStateCallback(object):
    # Host callbacks
    #

    @staticmethod
    def host_before_connect(state, host):
        pass

    @staticmethod
    def host_connect(state, host):
        pass

    @staticmethod
    def host_connect_error(state, host, error):
        pass

    @staticmethod
    def host_disconnect(state, host):
        pass

    # Operation callbacks
    #

    @staticmethod
    def operation_start(state, op_hash):
        pass

    @staticmethod
    def operation_host_start(state, host, op_hash):
        pass

    @staticmethod
    def operation_host_success(state, host, op_hash):
        pass

    @staticmethod
    def operation_host_error(state, host, op_hash):
        pass

    @staticmethod
    def operation_end(state, op_hash):
        pass


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

    # Current op hash
    current_op_hash = None
    # Current op global args for use w/facts
    current_op_global_kwargs = None

    loop_counter = None
    loop_line = None
    loop_filename = None

    # Name of the current deploy
    in_deploy = False
    deploy_name = None
    deploy_kwargs = None
    deploy_data = None
    deploy_op_order = None

    print_noop_info = False  # print "[host] noop: reason for noop"
    print_fact_info = False  # print "loaded fact X"
    print_input = False
    print_fact_input = False
    print_output = False
    print_fact_output = False

    # Used in CLI
    deploy_dir = None  # base directory for locating files/templates/etc
    current_deploy_filename = None
    current_exec_filename = None

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
            # TODO: remove this
            if config.REQUIRE_PYINFRA_VERSION is None:
                config.REQUIRE_PYINFRA_VERSION = '>={0}'.format(config.MIN_PYINFRA_VERSION)
                logger.warning(
                    '`MIN_PYINFRA_VERSION` is deprecated, please use `REQUIRE_PYINFRA_VERSION`.',
                )
            else:
                logger.warning(
                    'Ignoring legacy `MIN_PYINFRA_VERSION` because '
                    '`REQUIRE_PYINFRA_VERSION` also exists.',
                )

        if config.REQUIRE_PYINFRA_VERSION is not None:
            running_version = parse_version(__version__)
            required_versions = Requirement.parse(
                'pyinfra{0}'.format(config.REQUIRE_PYINFRA_VERSION),
            )

            if running_version not in required_versions:
                raise PyinfraError((
                    'pyinfra version requirement not met '
                    '(requires {0}, running {1})'
                ).format(
                    config.REQUIRE_PYINFRA_VERSION,
                    __version__,
                ))

        if config.REQUIRE_PACKAGES is not None:
            if isinstance(config.REQUIRE_PACKAGES, (list, tuple)):
                requirements = config.REQUIRE_PACKAGES
            else:
                with open(path.join(self.deploy_dir, config.REQUIRE_PACKAGES)) as f:
                    requirements = [
                        line.split('#egg=')[-1]
                        for line in f.read().splitlines()
                    ]

            try:
                require(requirements)
            except ResolutionError as e:
                raise PyinfraError('Deploy requirements ({0}) not met: {1}'.format(
                    config.REQUIRE_PACKAGES, e,
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

        self.callback_handlers = []

        # Setup greenlet pools
        self.pool = Pool(config.PARALLEL)
        self.fact_pool = Pool(config.PARALLEL)

        # Connection storage
        self.ssh_connections = {}
        self.sftp_connections = {}

        # Private keys
        self.private_keys = {}

        # Assign inventory/config
        self.inventory = inventory
        self.config = config

        # Hosts we've activated at any time
        self.activated_hosts = set()
        # Active hosts that *haven't* failed yet
        self.active_hosts = set()
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
        for host in inventory:
            host.state = self

        self.initialised = True

        # Flag to track added users (via `server.user` operation calls). This is
        # specifically to address users not existing during fact gathering phase
        # causing failures with su_user/sudo_user. If we expect to add the user
        # those facts should not fail but default.
        self.will_add_users = []

    def will_add_user(self, username):
        return username in self.will_add_users

    def add_will_add_user(self, username):
        self.will_add_users.append(username)

    def to_dict(self):
        return {
            'op_order': self.get_op_order(),
            'ops': self.ops,
            'facts': self.facts,
            'meta': self.meta,
            'results': self.results,
        }

    def add_callback_handler(self, handler):
        if not isinstance(handler, BaseStateCallback):
            raise TypeError((
                '{0} is not a valid callback handler (use `BaseStateCallback`)'
            ).format(handler))
        self.callback_handlers.append(handler)

    def trigger_callbacks(self, method_name, *args, **kwargs):
        for handler in self.callback_handlers:
            func = getattr(handler, method_name)
            func(self, *args, **kwargs)

    @contextmanager
    def deploy(self, name, kwargs, data, in_deploy=True, deploy_op_order=None):
        '''
        Wraps a group of operations as a deploy, this should not be used
        directly, instead use ``pyinfra.api.deploy.deploy``.
        '''

        # Handle nested deploy names
        if self.deploy_name:
            name = '{0} | {1}'.format(self.deploy_name, name)

        # Store the previous values
        old_in_deploy = self.in_deploy
        old_deploy_name = self.deploy_name
        old_deploy_kwargs = self.deploy_kwargs
        old_deploy_data = self.deploy_data
        old_deploy_op_order = self.deploy_op_order
        self.in_deploy = in_deploy

        # Set the new values
        self.deploy_name = name
        self.deploy_kwargs = kwargs
        self.deploy_data = data
        self.deploy_op_order = deploy_op_order
        logger.debug('Starting deploy {0} (args={1}, data={2})'.format(
            name, kwargs, data,
        ))

        yield

        # Restore the previous values
        self.in_deploy = old_in_deploy
        self.deploy_name = old_deploy_name
        self.deploy_kwargs = old_deploy_kwargs
        self.deploy_data = old_deploy_data
        self.deploy_op_order = old_deploy_op_order

        logger.debug('Reset deploy to {0} (args={1}, data={2})'.format(
            old_deploy_name, old_deploy_kwargs, old_deploy_data,
        ))

    @contextmanager
    def preserve_loop_order(self, items):
        frameinfo = get_caller_frameinfo(frame_offset=1)  # escape contextlib
        self.loop_line = frameinfo.lineno
        self.loop_filename = frameinfo.filename

        def item_generator():
            for i, item in enumerate(items, 1):
                self.loop_counter = i
                yield item

        yield item_generator

        self.loop_counter = None
        self.loop_line = None
        self.loop_filename = None

    def get_op_order(self):
        line_numbers_to_hash = self.op_line_numbers_to_hash
        sorted_line_numbers = sorted(list(line_numbers_to_hash.keys()))

        return [
            line_numbers_to_hash[numbers]
            for numbers in sorted_line_numbers
        ]

    def get_op_meta(self, op_hash):
        return self.op_meta[op_hash]

    def get_op_data(self, host, op_hash):
        return self.ops[host][op_hash]

    def activate_host(self, host):
        '''
        Flag a host as active.
        '''

        logger.debug('Activating host: {0}'.format(host))

        # Add to *both* activated and active - active will reduce as hosts fail
        # but connected will not, enabling us to track failed %.
        self.activated_hosts.add(host)
        self.active_hosts.add(host)

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

    def get_temp_filename(self, hash_key=None, hash_filename=True):
        '''
        Generate a temporary filename for this deploy.
        '''

        if not hash_key:
            hash_key = six.text_type(uuid4())

        if hash_filename:
            hash_key = sha1_hash(hash_key)

        return '{0}/pyinfra-{1}'.format(self.config.TEMP_DIR, hash_key)
