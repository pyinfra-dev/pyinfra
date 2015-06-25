# piynfra
# File: example/api_deploy.py
# Desc: example of how to deploy via the pyinfra API

from gevent import monkey
monkey.patch_all() # async things (speed++, optional)

import json
import logging

from pyinfra import state

from pyinfra.api import Inventory, Config, State
from pyinfra.api.operation import add_op
from pyinfra.api.operations import run_ops
from pyinfra.api.ssh import connect_all
from pyinfra.api.facts import get_facts

from pyinfra.modules import server, files


# Enable pyinfra logging
logging.basicConfig(level=logging.WARNING)
logging.getLogger('pyinfra').setLevel(logging.INFO)

# First we setup some inventory we want to target
# the first argument is a tuple of (list all all hosts, global/ALL data)
inventory = Inventory(
    ([
        'centos6.pyinfra',
        # Host-specific data can be attached in inventory
        ('centos7.pyinfra', {'systemd': True}),
        'ubuntu14.pyinfra',
        'debian7.pyinfra',
        'openbsd56.pyinfra'
    ], {
        # Global/ALL data can be attached
        'ssh_user': 'vagrant',
        'ssh_key': './files/insecure_private_key'
    }), bsd=([
        'openbsd56.pyinfra'
    ], {
        # Group-specific data can be attached like so
        'app_dir': '/opt/pyinfra/bsd'
    }), centos=([
        'centos6.pyinfra',
        'centos7.pyinfra'
    ], {})
)

# Now we create a new config (w/optional args)
config = Config(
    FAIL_PERCENT=50
)

# Setup the pyinfra state for this deploy
state.set(State(inventory, config))

# Connect to all the hosts
connect_all()

# Now we can build up a list of operations to run (running facts as required)
add_op(
    server.user,
    'pyinfra',
    home='/home/pyinfra',
    shell='/bin/bash',
    sudo=True
)

# Ensure the state of files
add_op(
    server.file,
    '/var/log/pyinfra.log',
    user='pyinfra',
    group='pyinfra',
    mode='644',
    sudo=True
)

# Ensure the state of directories
add_op(
    server.directory,
    '/tmp/email',
    user='pyinfra',
    group='pyinfra',
    mode='755',
    sudo=True
)

# Copy local files to remote host
add_op(
    files.put,
    'files/file.txt',
    '/home/vagrant/file.txt'
)

# And finally we run the ops
run_ops()

# We can also get facts for all the hosts
facts = get_facts('linux_distribution')
print json.dumps(facts, indent=4)
