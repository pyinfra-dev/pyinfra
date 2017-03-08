# v0.3 (WIP)

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
+ Removed compatability for deprecated changes in v0.2

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

To-be-breaking changes (deprecated & will be removed in 0.3):

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
+ Compatability tested w/Ubuntu/CentOS/Debian/OpenBSD/Fedora
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
