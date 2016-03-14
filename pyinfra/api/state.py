# pyinfra
# File: pyinfra/api/state.py
# Desc: class that represents the current pyinfra.state

from uuid import uuid4
from inspect import getargspec

from gevent.pool import Pool

from .config import Config
from .util import sha1_hash


class PipelineFacts(object):
    def __init__(self, state):
        self.state = state

    def __enter__(self):
        self.state.pipelining = True
        self.state.ops_to_pipeline = []
        self.state.facts_to_pipeline = {}

    def __exit__(self, type, value, traceback):
        self.state.pipelining = False

        # Get pipelined facts!
        print self.state.facts_to_pipeline

        # Actually build our ops
        for (func, state, host, args, kwargs) in self.state.ops_to_pipeline:
            func(state, host, *args, **kwargs)

    def process(self, func, decorated_func, args, kwargs):
        pipeline_facts = getattr(decorated_func, 'pipeline_facts', {})

        if pipeline_facts:
            func_args = list(getargspec(func).args)
            func_args = func_args[2:]

            for fact_name, arg_name in pipeline_facts.iteritems():
                index = func_args.index(arg_name)

                if len(args) >= index:
                    fact_arg = args[index]
                else:
                    fact_arg = kwargs.get(arg_name)

                if fact_arg:
                    self.state.facts_to_pipeline.setdefault(fact_name, set()).add(fact_arg)


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

    # Used in CLI
    deploy_dir = None
    active = True

    def __init__(self, inventory, config=None):
        self.ssh_connections = {}
        self.sftp_connections = {}

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

    def get_temp_filename(self, hash_key=None):
        if not hash_key:
            hash_key = str(uuid4())

        temp_filename = sha1_hash(hash_key)
        return '{0}/{1}'.format(self.config.TEMP_DIR, temp_filename)
