from gevent import monkey  # noqa
monkey.patch_all()  # noqa async things (speed++, optional)

import logging  # noqa: E402, I100

from collections import defaultdict  # noqa: E402

from pyinfra.api import BaseStateCallback, Config, Inventory, State  # noqa: E402
from pyinfra.api.connect import connect_all  # noqa: E402
from pyinfra.api.connectors.vagrant import make_names_data  # noqa: E402
from pyinfra.api.facts import get_facts  # noqa: E402
from pyinfra.api.operation import add_op  # noqa: E402
from pyinfra.api.operations import run_ops  # noqa: E402
from pyinfra.operations import files, server  # noqa: E402
from pyinfra_cli.prints import jsonify  # noqa: E402


# Enable pyinfra logging
class StateCallback(BaseStateCallback):
    @staticmethod
    def operation_start(state, op_hash):
        print('Start operation: {0}'.format(op_hash))

    @staticmethod
    def operation_end(state, op_hash):
        print('End operation: {0}'.format(op_hash))


logging.basicConfig(level=logging.CRITICAL)


# Make our hosts and groups data (using the Vagrant connector in this case)
hosts = []
groups = defaultdict(lambda: ([], {}))

for name, data, group_names in make_names_data():
    hosts.append((name, data))
    for group_name in group_names:
        if name not in groups[group_name][0]:
            groups[group_name][0].append(name)


# First we setup some inventory we want to target
# the first argument is a tuple of (list all all hosts, global/ALL data)
inventory = Inventory((hosts, {}), **groups)

# Now we create a new config (w/optional args)
config = Config(
    FAIL_PERCENT=81,
    CONNECT_TIMEOUT=5,
)

# Setup the pyinfra state for this deploy
state = State(inventory, config)
state.add_callback_handler(StateCallback())


# Connect to all the hosts
print('Connecting...')
connect_all(state)


# Start adding operations
print('Generating operations...')
add_op(
    state, server.user,
    'pyinfra',
    home='/home/pyinfra',
    shell='/bin/bash',
    sudo=True,
)

add_op(
    state, server.group,
    'pyinfra2',
    name='Ensure pyinfra2 group exists',
    sudo=True,
    # Add an op only to a subset of hosts
    # (in this case, the inventory.centos group)
    hosts=inventory.get_group('centos'),
)

# Ensure the state of files
add_op(
    state, files.file,
    '/var/log/pyinfra.log',
    user='pyinfra',
    group='pyinfra',
    mode='644',
    sudo=True,
)

# Ensure the state of directories
add_op(
    state, files.directory,
    '/tmp/email',
    user='pyinfra',
    group='pyinfra',
    mode='755',
    sudo=True,
)

# Copy local files to remote host
add_op(
    state, files.put,
    'files/file.txt', '/home/vagrant/file.txt',
)


# And finally we run the ops
run_ops(state)


# We can also get facts for all the hosts
facts = get_facts(state, 'os')
print(jsonify(facts, indent=4))
