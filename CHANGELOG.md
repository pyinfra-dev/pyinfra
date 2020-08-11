# v1.1.dev0

This is a big release with some major additions & improvements on `v1`:

+ Add `@dockerssh` connector that enables pyinfra to **build Docker containers on remote machines over SSH** (@charles-l)
+ Add global `precondition` and `postcondition` operation arguments
+ Implement state callback classes dramatically improving the API experience (see `examples/api_deploy.py`)
+ Start modifying facts during fact gathering phase, resolving common issues with interdependent operations, expand documentation on this (see: https://docs.pyinfra.com/en/latest/deploy_process.html#interdependent-operations)

Smaller bits:

+ Validate existing files in `file.download` with checksum arguments (@sysadmin75)
+ Stop stripping fact output (fixes `command` fact, @sysadmin75)
+ Add `--use-sudo-password` CLI argument
+ Fix using sudo password with a SSH user that doesn't have access to `/tmp`
+ Fix `python.call` docstring (@leahneukirchen)
+ Fix `--serial` and `--no-wait` executing operations twice
+ Improve autocomplete/intellisense handling of pseudo modules `pyinfra.[host|state|inventory]`


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
