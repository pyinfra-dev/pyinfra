# pyinfra

pyinfra automates service deployment. It does this by diffing the state of the server with the state defined in the deploy script. Deploys are asyncronous and highly performant. The inventory & deploy are managed with pure Python, allowing for near-infinite extendability.

+ [Quick start](./docs/quick_start.md)
+ [Documentation](./docs/README.md)
+ [Example deploy](./example)

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

pyinfra targets POSIX compatability and is currently tested against Ubuntu, Debian, CentOS & OpenBSD.
