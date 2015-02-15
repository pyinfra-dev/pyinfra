# pyinfra

pyinfra is a deployment tool. It's configured in Python; to make a deploy you need a `config.py` and `deploy.py`. Configs contain some basic information about the group of servers you wish to deploy to. The deploy script contains **operations**, which lie at the core of pyinfra.

Install pyinfra with pip: `pip install pyinfra`.

To get started you need a config script containing SSH details, for example:

```py
SSH_HOSTS = ['20.20.20.20']
SSH_USER = 'remote_user'
SSH_KEY = '/path/to/private_key'
```

And then deploy script containing the state you wish to apply:

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

# We can also check state and change our deploy accordingly
if server.fact('Distribution')['name'] == 'CentOS':
    yum.packages(
        ['a-package'],
        present=True
    )
```

Documentation for each of the modules can be found under `./modules`.
