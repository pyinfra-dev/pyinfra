# v0.5 (WIP)

+ **Vagrant integration**:

```sh
# Run a deploy on all Vagrant machines (vagrant status list)
pyinfra @vagrant deploy.py

# Can be used in tandem with other inventory:
pyinfra @vagrant,my-host.net deploy.py
pyinfra @vagrant,@local,my-host.net fact os
```

Operations/facts:
+ Add `gpgkey` argument to the `yum.repo` operation
+ Add `lsb_release` fact

General:
+ Add data defaults to `@deploy` functions, meaning third party pyinfra packages can provide sensible defaults that the user can override individually
+ Make it possible to pass group names (as strings) to `state.limit_hosts`
+ Improved error output when connecting
+ Update testing box from Ubuntu 15 to Ubuntu 16
+ Ensure `~/.ssh` exists keyscanning in `ssh.keyscan`
+ Don't include tests during setup!


# v0.4.1

+ Add `vzctl.unmount` operation (missing from 0.4!)
+ Add script to generate empty test files
+ Increase module test coverage significantly
+ Fix incorrect args in `vzctl.restart` operation
+ Fix `save=False` kwarg on `vzctl.set` not affecting command output (always saved)
+ Fix `gem.packages` install command

# v0.4

+ **Major change**: entirely new, streamlined CLI. Legacy support will remain for the next few releases. Usage is now:

```sh
# Run one or more deploys against the inventory
pyinfra INVENTORY deploy_web.py [deploy_db.py]...

# Run a single operation against the inventory
pyinfra INVENTORY server.user pyinfra,home=/home/pyinfra

# Execute an arbitrary command on the inventory
pyinfra INVENTORY exec -- echo "hello world"

# Run one or more facts on the inventory
pyinfra INVENTORY fact linux_distribution [users]...
```

+ **Major addition**: new `connectors` module that means hosts are no longer limited to SSH targets. Hostnames prefixed in `@` define which non-SSH connector to use. There is a new `local` connector for executing directly on the local machine, use hostname `@local`, eg:

```sh
pyinfra @local fact arch
```

+ **Major addition**: add `@deploy` wrapper for pyinfra related modules (eg [pyinfra-openstack](https://github.com/Oxygem/pyinfra-openstack)) to wrap a deploy (collection of operations) under one function, eg:

```py
from pyinfra.api import deploy

@deploy('Install Openstack controller')
def install_openstack_controller(state, host):
    apt.packages(
        state, host,
        {'Install openstack-client'},
        ['openstack-client'],
    )
    ...
```

+ Add **SSH module** to execute SSH from others hosts: `ssh.keyscan`, `ssh.command`, `ssh.upload`, `ssh.download`
+ Add **vzctl module** to manage OpenVZ containers: `vzctl.create`, `vzctl.stop`, `vzctl.start`, `vzctl.restart`, `vzctl.delete`, `vzctl.set`
+ Add `on_success` and `on_error` callbacks to all operations (args = `(state, host, op_hash)`)
+ Add `server.script_template` operation
+ Add global `hosts` kwarg to all operations, working like `local.include`'s
+ Add `cache_time` kwarg to `apt.update` operation
+ Add `Inventory.get_group` and `Inventory.get_host`
+ Inventory `__len__` now (correctly) looks at active hosts, rather than all
+ Add `Inventory.len_all_hosts` to replace above bug/qwirk
+ Add progress spinner and % indicator to CLI
+ Replace `docopt`/`termcolor` with `click`
+ Moved `pyinfra.cli` to `pyinfra_cli` (internal breaking)
+ Switch to setuptools `entry_points` instead of distutils scripts
+ Expand Travis.ci testing to Python 3.6 and 3.7 nightly
+ Remove unused kwargs (`sudo`, `sudo_user`, `su_user`) from `pyinfra.api.facts.get_facts`

To-be-breaking changes (deprecated):

+ Deprecate `add_limited_op` function, use `hosts` kwarg on `add_op`
+ Deprecate group access via attribute and host access via index on `Inventory`
    * `Inventory.get_group` and `inventory.get_host` replace


# v0.3

+ Add `init.service` operation
+ Add `config.MIN_PYINFRA_VERSION`
+ Add `daemon_reload` to `init.systemd`
+ Add `pip` path to `pip.packages` (@hoh)
+ Add `virtualenv_kwargs` to `pip.packages`
+ Add `socket` fact
+ Display meta and results in groups
+ Fact arguments now parsed with jinja2 like operation args
+ Use full dates in `file`, `directory` and `link` facts
+ Improve `--run` check between operation and/or shell
+ Improve tests with facts that have multiple arguments
+ Fix how `pip.packages` handles pip path
+ Fix `yum.rpm` when downloading already installed rpm's
+ Fix `users` fact with users that have no home directory
+ Fix command overrides with dict objects (git.repo)
+ Removed compatibility for deprecated changes in v0.2


# v0.2.2

+ Fix bug in parsing of network interfaces
+ Fix `--limit` with a group name


# v0.2.1

+ Use wget & pipe when adding apt keys via URL, rather than `apt-key adv` which breaks with HTTPs
+ Fix bug where file-based group names were uppercased incorrectly (ie dev.py made group DEV, rather than dev)


# v0.2

New stuff:

+ Add LXD facts/module
+ Add iptables facts/module
+ Support usernames with non-standard characters (_, capitals, etc)
+ Add global `get_pty` kwarg for all operations to work with certain dodgy programs
+ Add `--fail-percent` CLI arg
+ Add `exclude` kwarg to `files.sync`
+ Enable `--limit` CLI arg to be multiple, comma separated, hostnames
+ Add `no_recommends` kwarg to `apt.packages` operation
+ Make local imports work like calling `python` by adding `.` to `sys.path` in CLI
+ Add key/value release meta to `linux_distribution` fact
+ Improve how the init module handles "unknown" services
+ Add `force` kwarg to `apt.packages` and `apt.deb` and don't `--force-yes` by default

To-be-breaking changes (deprecated):

+ Switch to lowercase inventory names (accessing `inventory.bsd` where the group is defined as `BSD = []` is deprecated)
+ Rename `yum.upgrade` -> `yum.update` (`yum.upgrade` deprecated)
+ Deprecate `pip_virtualenv_packages` fact as `pip_packages` will now accept an argument for the virtualenv
+ Deprecate `npm_local_packages` fact as `npm_packages` will accept an argument for the directory

Internal changes:

+ Operations now `yield`, rather than returning lists of commands


# v0.1.5

+ Fix `--run` arg parsing splutting up `[],`


# v0.1.4

+ Enable passing of multiple, comma separated hosts, as inventory
+ Use `getpass`, not `raw_input` for collecting key passwords in CLI mode


# v0.1.3

+ Fix issue when removing users that don't exist


# v0.1.2

+ Improve private key error handling
+ Ask for encrypted private key passwords in CLI mode


# v0.1.1

+ Don't generate set groups when `groups` is an empty list in `server.user`.


# v0.1

+ First versioned release, start of changelog
+ Full docs @ pyinfra.readthedocs.io
+ Core API with CLI built on top
+ Two-step deploy (diff state, exec commands)
+ Compatibility tested w/Ubuntu/CentOS/Debian/OpenBSD/Fedora
+ Modules/facts implemented:
    * Apt
    * Files
    * Gem
    * Git
    * Init
    * Npm
    * Pip
    * Pkg
    * Python
    * Server
    * Yum
