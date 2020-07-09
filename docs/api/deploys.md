# Packaging Deploys

Operations in `pyinfra` execute low-level system tools (filesystem, systemd, package manager, etc). A **deploy** is a higher level abstraction, combining one or more operations together to setup and configure something (docker, certbot, nginx, etc).

Deploys are usually defined by the user (see [writing deploys](../deploys)). It is also possible to package deploys as Python modules making them reusable and shareable via [pypi](https://pypi.org/). These can then be imported into your own deploy code and utilised.

Packaging a deploy essentially requires two changes from the usual deploy code:

+ Wrap everything in a function, itself decorated with `@deploy(NAME)`
+ Include `state, host` as the first two arguments of any call to operations

```py
from pyinfra.api import deploy
from pyinfra.operations import apt

@deploy('Install MariaDB')
def install_mariadb(state, host):
    apt.packages(
        state, host,  # note passing of state & host here
        name='Install MariaDB apt package',
        packages=['mariadb-server'],
    )
```

This could then be used like so:

```py
# my_deploy.py

from packaged_deploy import install_mariadb
install_mariadb()
```

See the [`pyinfra-docker`](https://github.com/Fizzadar/pyinfra-docker) repository for an example of a packaged deploy.

## Global Arguments

Deploys accept the same [global arguments as as operations](/deploys.html#global-arguments) and they apply to every operation call within that deploy. Taking the above example:


```py

from packaged_deploy import install_mariadb
install_mariadb(sudo=True)
```

## Data in Deploys

Deploys can define their own set of data defaults. Any user provided host or group data with the same name will take precedent. This enables deploys to provide their own sensible default options and enable end-users to customise this by modifying group/host data.

```py
from pyinfra.api import deploy, DeployError

DEFAULTS = {
    'etcd_version': '1.2.3',
}

@deploy('Install mariadb', data_defaults=DEFAULTS)
def install_mariadb(state, host):
    if not host.data.mariadb_version:
        raise DeployError(
            'No mariadb_version set for this host, refusing to install mariadb!',
        )
    ...
```
