# pyinfra
# File: pyinfra/api/state.py
# Desc: class that represents the current pyinfra.state

from uuid import uuid4

from gevent.pool import Pool

from .config import Config
from .util import sha1_hash


class State(object):
    '''
    Create a new state based on the default state.
    '''

    inventory = None  # a pyinfra.api.Inventory which stores all our pyinfra.api.Host's
    config = None  # a pyinfra.api.Config

    pool = None  # main gevent pool

    in_op = False  # whether we are in an @operation (so inner ops aren't wrapped)

    # Current op args tuple (sudo, sudo_user, ignore_errors) for use w/facts
    current_op_meta = None

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

    def get_temp_filename(self, hash_key=None):
        if not hash_key:
            hash_key = str(uuid4())

        temp_filename = sha1_hash(hash_key)
        return '{0}/{1}'.format(self.config.TEMP_DIR, temp_filename)
