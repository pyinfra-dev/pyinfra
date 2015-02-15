# pyinfra

pyinfra helps to automate service deployment. It does this by diffing the state of the server with the state defined in the deploy script. Deploys are asyncronous and highly performant. The deploy & config scripts are written in pure Python, allowing for near-infinite extendability.

+ [Documentation](https://pyinfra.readthedocs.org)
+ [Example](./example)


## Example deploy script

```py
from pyinfra.modules import server, linux, apt, yum

# Ensure the state of a user
linux.user(
    'pyinfra',
    home='/home/pyinfra',
    shell='/bin/bash',
    public_keys=['abc'],
    sudo=True
)

# Ensure the state of files
linux.file(
    '/var/log/pyinfra.log',
    user='pyinfra',
    group='pyinfra',
    permissions='644'
)

# Work with multiple linux distributions
if server.fact('Distribution')['name'] == 'CentOS':
    # yum package manager
    yum.packages(
        ['python-devel', 'git'],
        sudo=True
    )
else:
    # apt package manager
    apt.packages(
        ['python-dev', 'git', 'nginx'],
        update=True,
        sudo=True
    )

# Execute arbitrary shell commands
server.shell(
    'echo "hello"'
)

# Manage init.d services
linux.init(
    'cron',
    restarted=True,
    ignore_errors=True
)
```
