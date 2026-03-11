# Compatibility

This page describes the compatibility guarantees pyinfra offers.


## pyinfra Versions

Where possible pyinfra follows [semantic versioning](https://semver.org/) rules. This means no breaking changes between minor versions (`1.0` -> `1.1`). Such changes are reserved for major version increases only. pyinfra will also generate warnings in CLI mode for any deprecated features due to be removed at the next major release. These are the pyinfra specific semver rules:

+ **Major**: breaking changes, warnings will show on latest previous major version
+ **Minor**: new operations, new APIs, new global arguments, deprecate & add warnings
+ **Patch**: new operation arguments for existing operations, bug fixes, documentation updates

## Control Systems

pyinfra works on anywhere that runs Python - Mac, Linux & Windows are all supported.

### Editor Integration

#### PyCharm

To debug pyinfra within PyCharm, you need to [explicitly enable support for Gevent](https://blog.jetbrains.com/pycharm/2012/08/gevent-debug-support/).


## Remote Systems

pyinfra aims to be compatible with all Unix-like operating systems and is currently developed against:

+ Linux distros:
    * Ubuntu 20/22/24
    * Debian 9/10
    * Fedora 43
    * Alpine 3.8
+ BSD flavours:
    * OpenBSD 6
    * FreeBSD 12
    * NetBSD 9
    * HardenedBSD 11
    * DragonflyBSD 5
+ OpenSUSE (leap15 + tumbleweed)
+ macOS 10.15 (with [`@local` connector](./connectors/local))
+ Docker (with [`@docker` connector](./connectors/docker))

In general, the only requirement on the remote side is shell access. POSIX commands are used where possible for facts and operations, so most of the ``server`` and ``files`` operations should work anywhere POSIX.


## Upgrading pyinfra from ``2.x`` -> ``3.x``

- Rename `_use_sudo_password` argument to `_sudo_password`
- Deploy decorator must be called:

```py
# Old, 2.x decorator
@deploy
def mydeploy():
    ...

# New, 3.x decorator
@deploy()
def mydeploy():
    ...
```

- Remove `@winrm` connector, will come back as [`pyinfra-windows`](https://github.com/pyinfra-dev/pyinfra-windows)

## Upgrading pyinfra from ``1.x`` -> ``2.x``

- Python 2.7 (finally!), 3.5 support dropped, Python 3.6 is now the minimum required version
- The "deploy directory" concept has been removed - everything now executes from the current working directory which removes the ambiguous magic v1 used to pick a deploy directory. A new --chdir CLI flag has been added to set the working directory before pyinfra executes

## Upgrading pyinfra from ``0.x`` -> ``1.x``

The move to `v1` removes a lot of old legacy functionality in pyinfra - there will be warnings written to the user in CLI mode if any of these are encountered. The full list can be seen [on the changelog](https://github.com/Fizzadar/pyinfra/blob/master/CHANGELOG.md#v1). In addition to these removals, `v1` brings a few major changes and deprecates the old methods. Again, pyinfra will output warnings when these are encountered, and support will be removed in `v2`.

### Rename the modules module

`v1` has moved where operations are imported from to make more sense:

```py
# Old, 0.x import:
from pyinfra.modules import server

# New, 1.x import:
from pyinfra.operations import server
```

### Naming operations

`v1` adds a global `name` argument to all operations. This replaces passing a `set` as the first argument which was confusing:

```py
# Old, 0.x style:
server.shell(
    {'Execute some shell'},
    commands=['someshell'],
)

# New, 1.x style:
server.shell(
    name='Execute some shell',
    commands=['someshell'],
)
```
