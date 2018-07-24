# piynfra
# File: example/api_deploy.py
# Desc: example of how to deploy via the pyinfra API

from gevent import monkey  # noqa
monkey.patch_all()  # noqa async things (speed++, optional)

import json  # noqa
import logging

from collections import defaultdict

from pyinfra.api import Config, Inventory, State
from pyinfra.api.connect import connect_all
from pyinfra.api.connectors.vagrant import make_names_data
from pyinfra.api.facts import get_facts
from pyinfra.api.operation import add_op
from pyinfra.api.operations import run_ops
from pyinfra.modules import files, server

from pyinfra_cli.prints import jsonify


# Enable pyinfra logging
logging.basicConfig(level=logging.WARNING)
logging.getLogger('pyinfra').setLevel(logging.INFO)


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
    TIMEOUT=5,
)

# Setup the pyinfra state for this deploy
state = State(inventory, config)


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
    {'Ensure pyinfra2 group exists'},  # set as the first arg names the operation
    'pyinfra2',
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
