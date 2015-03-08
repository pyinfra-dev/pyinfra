# pyinfra

pyinfra helps to automate service deployment. It does this by diffing the state of the server with the state defined in the deploy script. Deploys are asyncronous and highly performant. The deploy & config scripts are written in pure Python, allowing for near-infinite extendability.

+ [Documentation](./docs/README.md)
+ [Example](./example)

![](./example/example_deploy.png)

## Example deploy script

```py
from pyinfra import host
from pyinfra.modules import server, apt, yum

# Ensure the state of a user
server.user(
    'pyinfra',
    home='/home/pyinfra',
    shell='/bin/bash',
    public_keys=['abc'],
    sudo=True
)

# Ensure the state of files
server.file(
    '/var/log/pyinfra.log',
    user='pyinfra',
    group='pyinfra',
    permissions='644'
)

# Work with multiple linux distributions
if host.distribution['name'] == 'CentOS':
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
server.init(
    'cron',
    restarted=True,
    ignore_errors=True
)
```
