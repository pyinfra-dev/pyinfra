# v1.4.13

+ Fix `exclude_dir` in `files.sync` operation (@gchazot)
+ Fix multiple nested imports by properly resetting current exec filename
+ Improve error when there are no Vagrant instances and a name is provided

# v1.4.12

+ Support tag names in `git.GitBranch` fact (@stevenkaras)
+ Fix `cache_time` test in `files.download` operation (@stevenkaras)
+ Fix parsing of `server.LinuxDistribution` fact for Archlinux (@TypicalFence)
+ Correctly return `None` when no major version in `server.LinuxDistribution` fact

# v1.4.11

+ Fix removal of askpass file in `server.reboot` operation

# v1.4.10

+ Ensure services in `/usr/local/etc/rc.d` are handled in `bsdinit.service` operation
+ Check status of services in `/usr/local/etc/rd.d` in `bsdinit.RcdStatus` fact
+ Fix status checking in `bsdinit.RcdStatus` fact (for non-OpenBSD)
+ Expand BSD test boxes to include NetBsd & HardenedBSD

# v1.4.9

+ Fix connection w/`use_remote_sudo` in `ssh.upload` operation (@GerardoGR)
+ Fix `mysql.MysqlUserGrants` fact regex for `*.*` grant lines
+ Remove any askpass file before issuing reboots in `server.reboot` operation

# v1.4.8

+ Remove broken "will add user" detection in facts, just pass if user is missing
+ Quite non-string elements in `StringCommand` before passing to `shlex.quote`
+ Ignore `use_sudo_password` in the `@docker` connector
+ Loosen `jinja2` requirement to allow v3 (compatible)

# v1.4.7

+ Fix for passing `Path` objects as arguments to `files.*` operations & facts
+ Futher improvements to the updated facts docs

# v1.4.6

+ Properly handle shell quoting of filenames in all `files.*` facts
+ Update `files.*` operations to use explicit fact imports
+ Update the docs to show explicit fact import style

# v1.4.5

+ Fix missing mysql connection arguments updating privileges `mysql.database` operation (@sfermigier)
+ Fix parallel upload of askpass files
+ Properly handle shell quoting of filenames, fixes filenames with shell characters/etc for all `files.*` operations

# v1.4.4

+ Fix brew casks fact for non-mac platforms

# v1.4.3

+ Fix user fact comments with spaces by refactoring the fact (@sysadmin75)
+ Fix parsing of tab delimited crontab files with special times (@hazayan)
+ Fix incorrect lowercasing of yum & dnf package names
+ Fix/enable passing `to_ports` as an integer in `iptables.rule` operation
+ Migrate iptables facts & operations to use explicit fact imports
+ Fix/implement idempotency in iptables operations

# v1.4.2

+ Fix/implement WinRM env support (@mfrg)
+ Fix/handle Brew 2.6+ new cask CLI (@morrison12)
+ Fix parsing of tab delimited crontab files (@hazayan)

# v1.4.1

+ Improve deploy directory detection to handle nested directories
+ Copy existing file/directory permissions in `files.sync` operation
+ Treat `exited` systemd services as running in `systemd.SystemdStatus` fact
+ Fix handling of `cache_time` in `apt.update` operation
+ Fix invalid `name` arguments in `windows.service`, `windows.file` & `windows.directory` operations
+ Only show invalid auth argument warnings when not the defaults
+ Test operation global argument clashes

# v1.4

Three major themes to this release:

**Explicit fact imports** - this replaces the magic `host.fact.X` variables with explicitly imported facts, for example:

```py
# previously: host.fact.apt_sources
from pyinfra.facts.apt import AptSources
host.get_fact(AptSources)

# previously: host.fact.file('/path/to/file')
from pyinfra.facts.files import File
host.get_fact(File, path='/path/to/file')

# also now possible (previously impossible):
host.get_fact(File, path='/path/to/file', sudo=True)
```

And the CLI changes accordingly:

```sh
# previously: pyinfra INVENTORY fact apt_sources
pyinfra INVENTORY fact apt.AptSources

# previously: pyinfra INVENTORY fact file:/path/to/file directory:/path/to/directory
pyinfra INVENTORY fact files.File path=/path/to/file files.Directory path=/path/to/directory
```

This is not yet standard across the project and will be updated in subsequent releases. This also finally enables using third party facts in a sensible and explict manner. Overall, this is a dramatic improvement to the `pyinfra` fact mechanism.

**Windows operations expansion** - massive thank you to @mfrg for implementing these, huge expansion of Windows facts & operations, making it possible to really use `pyinfra` with Windows targets (additions listed below).

**Idempotency testing** - verification of operation idempotency (calling the same op twice outputs no commands/changes the second time) through testing and a large expansion in verified idempotency. Operations can now specify themselves as non-idempotent when expected (for example, `server.shell`).

Operation & fact updates:

+ Add `server.packages` operation - generic package management using the default OS package manager
+ Add `pip.venv` operation - shortcut for `pip.virtualenv(venv=True, ...)`
+ Add `server.Path` fact
+ Add `rpm.RpmPackageProvides` fact & support package aliases for `yum.packages` & `dnf.packages` operations
+ Add `windows_files.download`, `windows_files.put` & `windows_files.link` operations (@mfrg)
+ Add `windows_files.WindowsLink`, `windows_files.WindowsSha1File`, `windows_files.WindowsSha256File` & `windows_files.WindowsMd5File` facts (@mfrg)

CLI updates:

+ New style fact gathering CLI arguments
+ Prefix SSH auth flags (`--user` becomes `--ssh-user`), deprecate old versions
+ Deprecate `--facts` & `--operations` CLI flags
+ Deprecate `all-facts` command
+ Hide deprecated options from `--help`

Other bits:

+ Show warnings when using invalid auth argument combinations (`sudo_user` without `sudo`, etc)
+ Bump minimum Paramiko version to `2.7`


# v1.3.12

+ Fix & test loading non-RSA SSH keys with passwords (@Yakulu)

# v1.3.11

+ Fix custom SSH config parsing to support latest Paramiko features (`Match` directives)
+ Fix error loading SSH keys with passwords (try all key formats before failing)

# v1.3.10

+ Properly escape postgresql role/database/owner operation commands (@RobWouters)
+ Add support for additional winrm transport types & options (@mfrg)
+ Fix for `Git*` facts where the target repo doesn't exist
+ Git branches update: `master` renamed to `current` and new `next` branch tracking next minor release
+ Contributing documentation page updated to include branch description

# v1.3.9

+ Use `StringCommand` to implement fact requires commands, fixes `mysql_*` facts with passwords
+ Improve error for invalid private key files, including message for old paramiko versions
+ Fix `files.line`/`files.replace`/`server.crontab` replacements containing quotes
+ Fix `@winrm` connector command execution
+ Improve `files.template` docstring (@Gaming4LifeDE)

# v1.3.8

+ Add Debian to prettified names in `LinuxDistribution` fact (@blarghmatey)
+ Fix logging non-string args (@morrison12)
+ Tidy up new issue templates (@Gaming4LifeDE)
+ Use `export` instead of `env` so variables pass into sub-commands as expected
+ pass any `env` into fact execution within operations
+ Fix splitting of inventory filename into group name
+ Improve package name parsing in `BrewPackages` fact
+ Only append blank line before new cron entries if some already exist
+ Remove any leftover askpass files when using `use_sudo_password`

# v1.3.7

+ Support reading custom user operations in CLI mode (@tsnoam)
+ Allow adding users with duplicate UIDs in `server.user` operation (@tsnoam)
+ Add user UID/GID to `users` fact output (@tsnoam)
+ Fix uninstall command in `apk.packages` operation (@Gaming4LifeDE)
+ Fix support for `add_deploy` in API mode
+ Rename (deprecate) facts `server.Os` -> `server.Kernel` & `server.OsVersion` -> `server.KernelVersion`
+ Add `server.MacosVersion` fact
+ Add an empty line before writing in named crontab entries
+ Fix check for command change with named crontab entries
+ Properly quote package names (fix Python version specifiers with shell characters in `pip.packages` operation)

# v1.3.6

+ Ignore errors when `crontab` fails (ie, when there's no crontab)
+ Update `crontab` fact in `server.crontab` operation
+ Update `sysctl` fact in `server.sysctl` operation

# v1.3.5

+ Add support for relative includes: `local.include('./relative_file.py')`
+ Fix parsing of special times in `server.Crontab` fact
+ Fix editing `special_time` in `server.crontab` operation
+ Fix printing of imported modules in group data files when using `debug-inventory`
+ Use/respect `__all__` if defined in group data files

# v1.3.4

+ Improve matching of user hostname in `mysql_user_grants` fact

# v1.3.3

+ Fix support for package names in `deb_package` fact (@s-vx)
+ Fix check for match any vs. all in ensure packages util (fixes Pacman package groups)
+ Fix/support passing keyword functions into facts
+ Fix parsing of `mysql_user_grants` fact output
+ Fix idempotency of `mysql.privileges` operation

# v1.3.2

+ Add `pacman_unpack_group` fact (@unai-ndz)
+ Support Pacman package groups properly in `packman.packages` operation (@unai-ndz)
+ Fix only load git config if the repo directory exists in `git.config` operation
+ Fix global git config loading when files don't exist in `git_config` fact
+ Fix deploys doc example operation (@makom)
+ Fix (add quoting) download URLs containing shell characters in `files.download` operation
+ Fix checking for rsync in `@local` connector

# v1.3.1

+ Add `git_tracking_branch` fact and rework `git.worktree` operation (@remybar)
+ Add `user_mode` arg to `systemd.daemon_reload` operation (@smdnv)
+ Add `comment` arg/support to `server.user` operation (@sprat)
+ Use `StrictUndefined` when rendering templates (@relaxdiego)
+ Allow numbers in `pacman_packages` fact
+ Remove restriction on group data types
+ Improve support for `Path` objects as operation arguments (@relaxdiego)
+ Improve error output when failing to start SFTP sessions (@relaxdiego)
+ Fix readme doc link (@mrshu)
+ Fix Docker tests and separate from main tests, don't run on PRs

# v1.3

Theme of this release is improving error handling and end user experience. Highlights:

+ Make most global arguments dynamic - support different `chdir`, `sudo`, etc for different hosts within the same operation call
+ Rework line number ordering to support any nested function calls and/or imports
+ Improve error handling for unexpected internal (pyinfra) and external (user code) errors
+ Detect and error when an operation calls another using global arguments
+ Properly fail when fact commands don't execute correctly vs. a given command not being present on the host, using `requires_command` fact attribute

Operation & fact updates:

+ Add `git.worktree` operation (@remybar)
+ Add `git.bare_repo` operation (@stchris)
+ Add `user_mode` argument to `systemd.service` operation (@jprltsnz)
+ Use `hostnamectl` where available for `server.hostname` operation
+ Use `uname -a` for `hostname` fact
+ Add `user` fact

Other bits:

+ Enable using `use_sudo_password` without `sudo=True`
+ Move testing & documentation processes to GitHub actions
+ Run tests on Windows & MacOS


# v1.2.1

+ Add `pip3_packages` fact
+ Improve/fix handling of `reboot` exit code in `server.reboot` operation
+ Restore `__eq__` functionality of pseudo modules
+ Add tests for the pseudo modules

# v1.2

Lots of smaller bits in this release and massive improvement to the documentation.

Operation & fact updates:

+ **Deprecate** `init.*` operations, renamed to: `systemd.service`, `upstart.service`, `launchd.service`, `bsdinit.service`, `sysvinit.service`, `sysvinit.enable`, `server.service`
+ Add `systemd.daemon_reload` operation
+ Add `files.rsync` operation
+ Add `port` and `user` arguments to all `ssh.*` operations
+ Add `apt_keys` fact and use in `apt.key` operation
+ Add GPG facts: `gkg_key`, `gpg_keys` and `gpg_secret_keys`
+ Add `additional_ips` in `network_devices` fact
+ Add `ipv4_addrs` and `ipv6_addrs` facts to replace `ipv[46]_addresses`
+ Add `linux_gui` & `has_gui` facts

Other bits:

+ Add global `chdir`, `preserve_su_env` and `su_shell` arguments
+ Add `Config.REQUIRE_PACKAGES` to check requirements befor execution
+ Add `host_before_connect` and `host_connect_error` state callback methods
+ Support multiple `--limit` CLI arguments
+ Allow passing an integer in `files.replace` replacement lines (@vindarel)
+ Use `curl` if `wget` not present in `apt.key` operation
+ Completely remove use of `use_default_on_error` in facts
+ Many updates/tweaks to documentation + theme
+ Allow functions in/as group/host data (CLI)
+ Implement/use Angolia docsearch on documentation


# v1.1.2

+ Add `port=22` argument to the `ssh.keyscan` operation
+ Add `extra_install_args` argument to the `pip.packages` operation
+ Support uninstalling a requirements file in the `pip.packages` operation
+ Use state in `files.replace` operation, enabling noop support where appropriate
+ Add a warning when using `use_su_login`
+ Fix parsing stat output when groups contain spaces (`file`, `directory`, `link` facts)
+ Fix minimum gevent version (@alexandervdm)

# v1.1.1

+ Don't fail for user error facts when the user will be added earlier in the deploy
+ Support `shasum` command in `files.download` operation
+ Consider waiting systemd units to be running (@i-do-cpp)
+ Improve regex for systemd units (support ones with `.`) (@i-do-cpp)
+ Fix sudo passwords with special characters (@sysadmin75)
+ Fix typo in host arg warning (@weakish)

# v1.1

This is a big release with some major additions & improvements on `v1`.

Highlights:

+ Start **modifying facts during fact gathering phase**, resolving common issues with interdependent operations, expand documentation on this ([docs](https://docs.pyinfra.com/page/deploy_process.html#interdependent-operations))
+ Implement **state callback classes** dramatically improving the API experience (see `examples/api_deploy.py`)
+ Add `@dockerssh` connector that enables pyinfra to **build Docker containers on remote machines over SSH** (@charles-l)
+ Add global `precondition` and `postcondition` operation arguments
+ Fix using `su_user` on BSD/MacOS systems
+ Rework verbosity flags and **add noop logging** (ie package X is already installed) ([docs](https://docs.pyinfra.com/page/cli.html#verbosity))

Notable change:

The `yum.packages` and `dnf.packages` operations have _changed_ their "version join" string value - both package managers use `-` to join name + version while allowing `-` in the name. This leads to ambiguous behaviour for packages containing dashes, as such the version join value has been changed to `=` - meaning it can now actually be used! This means to specify a specific version of a yum/dnf package you should use `<name>=<version>` rather than `<name>-<version>`.

Smaller bits:

+ Add `REQUIRE_PYINFRA_VERSION` config option (& deprecate `MIN_PYINFRA_VERSION`)
+ Validate existing files in `file.download` with checksum arguments (@sysadmin75)
+ Stop stripping fact output (fixes `command` fact, @sysadmin75)
+ Add `extra_install_args` and `extra_uninstall_args` kwargs to `apt.packages` operation
+ Add `--use-sudo-password` CLI argument
+ Normalise `server.sysctl` handling of string/int values
+ Improve autocomplete/intellisense handling of pseudo modules `pyinfra.[host|state|inventory]`
+ Fix using sudo password with a SSH user that doesn't have access to `/tmp`
+ Fix `python.call` docstring (@leahneukirchen)
+ Fix `--serial` and `--no-wait` executing operations twice
+ Fix `server.sysctl` usage with multiple values


# v1.0.4

+ Add `selinux` fact (@FooBarQuaxx)
+ Improve/fix `rpm_packages` fact parsing (@FooBarQuaxx)
+ Stop showing arguments on operations with names

# v1.0.3

+ Reimplement `file`/`directory`/`link` facts using `stat`
    * No breaking changes
    * Adds `ctime` and `atime` to the output dictionary
+ Add `backup` argument to the `files.line` and `files.replace` operations
+ Add `SimpleNamespace` to the list of allowed data types
+ Don't fail when the destination directory is a symlink in the `files.sync` operation
+ Fix running the same fact in CLI w/different arguments
+ Add local integration tests that check idempotency (of files operations only for now)

# v1.0.2

+ Further improve fact output when errors are encountered
    * Will now output stdout + stderr when a fact command fails unexpectedly
    * This brings the same instant debugging feel to facts that operations have
+ Fix `wget` failure handling in `files.download` operation (@artizirk)
+ Improve files facts handling when file/directory/link does not exist

# v1.0.1

+ Log host fact errors/warnings
+ Switch to `distro` package for `linux_distribution` fact (@FooBarQuaxx)
+ Expand support for `os.PathLike` path variables (@FooBarQuaxx)
+ Improve checking state/host presence when calling operations (@FooBarQuaxx)
+ Don't error in `sha1_file` fact when no file exists

# v1.0

The first `1.x` release!

This release deprecates a lot of old/legacy `pyinfra` code and brings fourth a new, stable API. So long as you see no warnings when executing `pyinfra`, upgrading should require no chanages.

What's new:

+ Add new global `name` argument to name operations (deprecate `set` as the first argument)
+ Improve unexpected fact error handling, bad exit codes will be treated as errors unless the fact explicitly expects this could happen (system package managers for example)
+ [CLI] write progress/user info/logs to `stderr` only
+ [API] Consistent ordering when `add_op` and `add_deploy` functions
+ [API] Return a dictionary of `host` -> `OperationMeta` when using `add_op`
+ Enable passing a list of modules to `server.modprobe` (@FooBarQuaxx)
+ Support `Path` objects in `files.[file|directory|link]` operations
+ Support `shasum` (MacOS) in `sha1_file` fact

Breaking changes:

+ Deprecate using `set` as the first/name argument for operations
+ Rename `files.*` arguments (`name` -> `path`, `destination` -> `dest`)
+ Rename `server.*` arguments (`name` -> `user|group|cron_name|key|path`, `filename` -> `src`)
+ Rename `mysql.*` + `postgresql.*` arguments (`name` -> `user|database|role`)
+ Rename `init.*` arguments (`name` -> `service`)
+ Rename `lxd.container` argument `name` -> `id`
+ Rename `git.repo` argumenets `source` -> `src` & `target` -> `dest`
+ Rename `iptables.chain` argument `name` -> `chain`
+ Rename `python.call` argument `func` -> `function`
+ Rename `size` -> `mask_bits` inside `network_devices` fact
+ Change default of `interpolate_variables` from `True` -> `False`
+ Remove deprecated`hosts`/`when`/`op` global operation arguments
+ Rename reprecated `Config.TIMEOUT` -> `Config.CONNECT_TIMEOUT`
+ Remove deprecated `use_ssh_user` argument from `git.repo` operation
+ Remove deprecated `python.execute` operation
+ Remove deprecated `Inventory.<__getitem__>` & `Inventory.<__getattr__>` methods
+ Remove deprecated `add_limited_op` function
+ Remove deprecated legacy CLI suppot

# v0.x

[See this file in the `0.x` branch](https://github.com/Fizzadar/pyinfra/blob/0.x/CHANGELOG.md).
