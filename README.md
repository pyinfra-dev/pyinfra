# pyinfra

pyinfra automates service deployment. It does this by diffing the state of the server with the state defined in the deploy script. Deploys are asyncronous and highly performant. The inventory & deploy are managed with pure Python, allowing for near-infinite extendability.

+ [Quick start](docs/quick_start.md)
+ [Documentation](docs/README.md)
+ [Example deploy](example)
+ [API Example](example/api_deploy.py)

When you run `pyinfra -i <inventory_file> <deploy_file>`, you'll see something like:

![](./docs/example_deploy.png)

A **inventory** file might look like:

```py
GROUP = [
    'my.hostname'
]
```

And a **deploy** file like:

```py
# These modules contain operations, which provide ways to set desired state
# for the remove service.
from pyinfra.modules import files, server

# Ensure the state of a user
server.user(
    'pyinfra',
    present=True,
    home='/home/pyinfra'
)

# Ensure the state of files
files.file(
    '/var/log/pyinfra.log',
    user='pyinfra',
    group='pyinfra',
    permissions='644',
    sudo=True
)
```

Alternatively, you can use the **Python API**:

```py
from pyinfra import state

from pyinfra.api import Inventory, State
from pyinfra.api.operation import add_op
from pyinfra.api.operations import run_ops
from pyinfra.api.ssh import connect_all
from pyinfra.api.facts import get_facts

from pyinfra.modules import files, server

# Setup inventory of target hosts
inventory = Inventory(
    ([
        'my.hostname'
    ], {}),
    ssh_user='user',
    ssh_key='/path/to/keyfile'
)

# Setup the pyinfra state for this deploy
state.new(State(inventory))

# Connect to all the hosts
connect_all()

# Now we can build up a list of operations to run (running facts as required)
add_op(
    server.user,
    'pyinfra',
    present=True,
    home='/home/pyinfra'
)

# Ensure the state of files
add_op(
    files.file,
    '/var/log/pyinfra.log',
    user='pyinfra',
    group='pyinfra',
    permissions='644',
    sudo=True
)

# And finally we run the ops
run_ops()
```

+ [CLI Example](example)
+ [API Example](example/api_deploy.py)
+ [Quick start](docs/quick_start.md)
+ [Documentation](docs/README.md)
