# Quick Start

Install pyinfra with pip: `pip install pyinfra`.

To get started you need an **inventory** file (`inventory.py`) containing groups of hostnames:

```py
# Any ALL_CAPS names are accepted
GROUP = [
    'my.hostname'
]
```

And then a **deploy** file (`deploy.py`) containing the state you wish to apply:

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
```

And to run the deploy:

```
pyinfra -i inventory.py deploy.py --user=vagrant --key=files/insecure_private_key
```

## What next?

Check out the [example deploy.py](../example/deploy.py) and [module documentation](./modules/README.md).
