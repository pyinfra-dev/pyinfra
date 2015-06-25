# Quick Start

Install pyinfra with pip: `pip install pyinfra`.

To get started you need a **config script** containing SSH details, for example:

```py
SSH_HOSTS = ['myhost.net']
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

# etc... see ./modules or the full example!
```

And to run the deploy:

`pyinfra -c config.py deploy.py`

## What next?

Check out the [example deploy.py](../example/deploy.py) and [module documentation](./modules/README.md).
