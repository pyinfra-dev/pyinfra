# Quick Start

Install pyinfra with pip: `pip install pyinfra`.

To get started you need a **config script** containing SSH details, for example:

```py
SSH_HOSTS = ['20.20.20.20']
SSH_USER = 'remote_user'
SSH_KEY = '/path/to/private_key'
```

And then **deploy script** containing the state you wish to apply:

```py
# These modules contain operations, which provide ways to set desired state
# for the remove service.
from pyinfra.modules import server, linux, yum

# Ensure the state of a user
linux.user(
    'pyinfra',
    present=True,
    home='/home/pyinfra'
)

# Ensure the state of files
server.file(
    '/var/log/pyinfra.log',
    user='pyinfra',
    group='pyinfra',
    permissions='644',
    sudo=True
)

# Ensure the state of directories
server.directory(
    config.ENV_DIR,
    user='pyinfra',
    group='pyinfra',
    permissions='755',
    recursive=True,
    sudo=True
)

# etc... see ./modules or the full example!
```

And to run the deploy:

`pyinfra -c config.py deploy.py`

## What next?

Check out the [module documentation](./modules/README.md).
