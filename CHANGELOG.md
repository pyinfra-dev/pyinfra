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
