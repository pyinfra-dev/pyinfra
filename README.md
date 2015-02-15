# pyinfra

pyinfra helps to automate service deployment. It does this by diffing the state of the server with the state defined in the deploy script. Deploys are generally asyncronous and highly performant. The deploy & config scripts are written in pure Python, allowing for infinite extendability.


## Synopsis

+ Install with `pip install pyinfra`
+ Create a `deploy.py` script:

```py
from pyinfra.modules import linux

# Ensure the state of a user
linux.user(
    'pyinfra',
    present=True,
    home='/home/pyinfra'
)

# Ensure the state of files
linux.file(
    '/var/log/pyinfra.log',
    present=True,
    user='pyinfra',
    group='pyinfra',
    permissions='644',
    sudo=True
)
```

+ And a `config.py` script:

```py
# SSH details
SSH_HOSTS = [
    '20.20.20.20',
    '20.20.20.21',
    '20.20.20.22'
]
SSH_PORT = 22
SSH_USER = 'remote_user'
SSH_KEY = '/path/to/private_key'
```

+ And then run with:

`pyinfra -c config.py deploy.py`

Check out [the full example](./example).
