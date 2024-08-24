# Packaging Deploys

Operations in pyinfra execute low-level system tools (filesystem, systemd, package manager, etc). A **deploy** is a higher level abstraction, combining one or more operations together to setup and configure something (docker, certbot, nginx, etc).

Deploys are usually defined by the user (see [Using Operations](../using-operations)). It is also possible to package deploys as Python modules making them reusable and shareable via [pypi](https://pypi.org/). These can then be imported into your own deploy code and utilised.

Packaging a deploy essentially requires two changes from the usual deploy code:

+ Wrap everything in a function decorated with `@deploy(NAME)`

```py
from pyinfra.api import deploy
from pyinfra.operations import apt

@deploy("Install MariaDB")
def install_mariadb():
    apt.packages(
        name="Install MariaDB apt package",
        packages=["mariadb-server"],
    )
```

This could then be used like so:

```py
from packaged_deploy import install_mariadb
install_mariadb()
```

## Examples

+ [`pyinfra-docker`](https://github.com/Fizzadar/pyinfra-docker) is a basic, no argument deploy that simply installs Docker
+ [`pyinfra-prometheus`](https://github.com/grantstephens/pyinfra-prometheus) is a more complex package containing multiple deploys that can be used to install Prometheus instances and various exporter services

## Global Arguments

Deploys accept the same [global arguments as operations](../arguments) and they apply to every operation call within that deploy. Taking the above example:


```py
from packaged_deploy import install_mariadb
install_mariadb(sudo=True)
```

## Data in Deploys

Deploys can define their own set of data defaults. Any user provided host or group data with the same name will take precedent. This enables deploys to provide their own sensible default options and enable end-users to customise this by modifying group/host data.

```py
from pyinfra import host
from pyinfra.api import deploy
from pyinfra.operations import apt

DEFAULTS = {
    "mariadb_version": "1.2.3",
}

@deploy("Install mariadb", data_defaults=DEFAULTS)
def install_mariadb():
    apt.packages(
        name="Install MariaDB apt package",
        packages=[f"mariadb-server={host.data.mariadb_version}"],
    )
```
