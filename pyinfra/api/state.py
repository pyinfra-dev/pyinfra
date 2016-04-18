# pyinfra
# File: pyinfra/api/state.py
# Desc: class that represents the current pyinfra.state

from __future__ import division, unicode_literals, print_function

from uuid import uuid4
from inspect import getargspec

import six
from gevent.pool import Pool

from pyinfra import logger

from .config import Config
# from .facts import get_facts
from .util import sha1_hash
from .exceptions import PyinfraError


class PipelineFacts(object):
    def __init__(self, state):
        self.state = state

    def __enter__(self):
        self.state.pipelining = True
        self.state.ops_to_pipeline = []
        self.state.facts_to_pipeline = {}

    def __exit__(self, type_, value, traceback):
        self.state.pipelining = False

        # Get pipelined facts!
        # for name, args in six.iteritems(self.state.facts_to_pipeline):
        #     get_facts(self.state, name, pipeline_args=args)

        # Actually build our ops
        for (host_name, func, args, kwargs) in self.state.ops_to_pipeline:
            logger.debug(
                'Replaying op: {0}, args={1}, kwargs={2}'.format(func, args, kwargs)
            )

            func(self.state, self.state.inventory[host_name], *args, **kwargs)

    def process(self, func, decorated_func, args, kwargs):
        pipeline_facts = getattr(decorated_func, 'pipeline_facts', None)

        if pipeline_facts:
            func_args = list(getargspec(func).args)
            func_args = func_args[2:]

            for fact_name, arg_name in six.iteritems(pipeline_facts):
                index = func_args.index(arg_name)

                if len(args) >= index:
                    fact_arg = args[index]
                else:
                    fact_arg = kwargs.get(arg_name)

                if fact_arg:
                    # Get the sudo/sudo_user state, because facts are uniquely hashed
                    # using their name, command and sudo/sudo_user.
                    sudo = kwargs.get('sudo', self.state.config.SUDO)
                    sudo_user = kwargs.get('sudo_user', self.state.config.SUDO_USER)

                    self.state.facts_to_pipeline.setdefault(
                        (fact_name, sudo, sudo_user), set()
                    ).add(fact_arg)


class State(object):
    '''
    Manages state for a pyinfra deploy.
    '''

    inventory = None  # a pyinfra.api.Inventory which stores all our pyinfra.api.Host's
    config = None  # a pyinfra.api.Config

    pool = None  # main gevent pool

    in_op = False  # whether we are in an @operation (so inner ops aren't wrapped)

    # Current op args tuple (sudo, sudo_user, ignore_errors) for use w/facts
    current_op_meta = None

    # Flag for pipelining mode
    pipelining = False

    # Flags for printing
    print_output = False  # print output from the actual deploy (-v)
    print_fact_info = False  # log fact gathering as INFO > DEBUG (-v)
    print_fact_output = False  # print output from facts (-vv)
    print_lines = False  # print blank lines between operations (always in CLI)

    # Used in CLI
    deploy_dir = None  # base directory for locating files/templates/etc
    active = True  # used to disable operation calls when scanning deploy.py for config

    def __init__(self, inventory, config=None):
        # Connection storage
        self.ssh_connections = {}
        self.sftp_connections = {}

        # Facts storage
        self.facts = {}
        self.fact_locks = {}

        if config is None:
            config = Config()

        if not config.PARALLEL:
            config.PARALLEL = len(inventory)

        # Assign inventory/config
        self.inventory = inventory
        self.config = config

        # Assign self to inventory & config
        inventory.state = config.state = self

        # Setup greenlet pool
        self.pool = Pool(config.PARALLEL)

        # Host tracking
        self.active_hosts = set()
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

    def fail_hosts(self, hosts_to_fail):
        # Remove the failed hosts
        self.inventory.active_hosts -= hosts_to_fail

        # Check we're not above the fail percent
        active_hosts = self.inventory.active_hosts

        if self.config.FAIL_PERCENT is not None:
            percent_failed = (1 - len(active_hosts) / len(self.inventory)) * 100
            if percent_failed > self.config.FAIL_PERCENT:
                raise PyinfraError('Over {0}% of hosts failed'.format(
                    self.config.FAIL_PERCENT
                ))

        # No hosts left!
        if not active_hosts:
            raise PyinfraError('No hosts remaining!')

    def get_temp_filename(self, hash_key=None):
        '''
        Generate a temporary filename for this deploy.
        '''

        if not hash_key:
            hash_key = str(uuid4())

        temp_filename = sha1_hash(hash_key)
        return '{0}/{1}'.format(self.config.TEMP_DIR, temp_filename)
