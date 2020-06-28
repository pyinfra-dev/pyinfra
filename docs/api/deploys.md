# Packaging Deploys

Operations represent low-level state that should be met and applied if needed. Deploys are more high-level, for example "install & configure service X". They represent a collection of operations. Like operations, deploys can be made into python packages making them reusable and shareable via [pypi](https://pypi.org/).

Writing a deploy is similar to [writing an operation](./modules):

```py
from pyinfra.api import deploy
from pyinfra.operations import apt

@deploy('Install MariaDB')
def install_mariadb(state, host):
    apt.packages(
        {'Install MariaDB apt package'},
        state, host,  # note passing of state & host here
        'mariadb-server',
    )
```

See the [`pyinfra-docker`](https://github.com/Fizzadar/pyinfra-docker) repository for an example of a packaged deploy.
