# v2.8

Added:

+ Add `device` and `fs_type` arguments to `server.mount` operation (@chriskingio)
+ Add `args` argument to `server.script_template` operation (@chriskingio)

Fixed:

+ Support FreeBSD in `server.user` & `server.group` operations (@wowi42)
+ Add missing `py.typed` flag to package
+ Fix lookup of systemd units containing `.` in the name (@cawo-odoo)
+ Strip newlines off public keys read from disk (@sysadmin75)
+ Properly escape database names in `mysql.database` operation (@tissieres)

# v2.7

Been a while since a release, so there's a bunch of great stuff in thise one!

Added:

+ Add experimental support for importing inventories from Python modules
+ Add `caro.packages` operation (@wowi42)
+ Add `server.locale` operation and `server.Locales` fact (@maisim)
+ Add `ensure_newline` keyword argument to `files.line` (@yunzheng)
+ Add `args` argument to `server.script` operation
+ Add make `put_file` work with `doas` (@minusf)
+ Handle adding git config key-values with multiple lines (@gchazot)

Fixed:

+ Add Ubuntu latest (22.04) to CI tests (@gchazot)
+ Fix codecov workflow (@ioO)
+ Escape & character during sed replacement during `line.replace` (@sysadmin75)
+ Fix last login time in `server.users` operation (@minusf)
+ Fix fact hash for short facts where the backing fact takes arguments

# v2.6.2

+ Add support for classic confinment in `snap.packages` operation (@pabloxio)
+ Support dictionaries for Terraform connector inventory
+ Upgrade to `distro>1.6` and remove patch hack
+ Fix `files.Md5File` fact for BSD style output (@ScottKevill)
+ Fix handling of `protocol` in `iptables.rule` operation (@sysadmin75)
+ Fix a large number of documentation issues
+ Add docstrings to `Host` methods
+ Cleanup duplicate code (@minusf)
+ Refactor has files facts (@ScottKevill)

# v2.6.1

+ Fix reuse of temporary file names in `server.script` operation (@link2xt)
+ Fix retry handling on SFTP errors

# v2.6

Added:

+ Use SSH connector parameters with `files.rsync` operation (@StevenKGER)
+ Add `auto_remove` arguments to `apt.upgrade` operation (@mcataford)
+ Make it possible to call any function/op/deploy from the CLI

Fixed:

+ Fix handling of ALL/GRANT OPTION permissions in `mysql.privileges` operation (@gchazot)
+ Fix `mysql.load` operation with spaces in filenames (@gchazot)
+ Fix fact `apk.ApkPackages` for packages with numbers in the name (@dchauviere)
+ Fix fact `openrc.OpenrcStatus` for services with start times (@dchauviere)
+ Fix `files.put` for files containing spaces in local connector (@uggedal)
+ Fix performance of fact phase when calling functions/operations directly in CLI

# v2.5.3

+ Fix handling of facts with no arguments or with global arguments
+ Fix mutable default breaking `Host.loop` position tracking
+ Cleanup exception handling within operation code

# v2.5.2

+ Fix/make safer check for sysvinit in `server.service` operation
+ Fix parsing of sticky/setgid/setuid permission bits in `files.*` facts
+ Respect `TMPDIR` when asking for sudo password (@jaysoffian)
+ Fix old windows fact names (@simon04)
+ Fix consistency of facts called in vs. out of operation context
+ Fix a bunch of pylint issues (@marksmayo)
+ Fix docstrings on `python.*` operations

# v2.5.1

+ Fix bug in pre/post condition handling that would print non-fatal errors

# v2.5

Added:

+ Add `selinux.boolean`, `selinux.file_context`, `selinux.file_context_mapping` & `selinux.port` operations (@morrison12)
+ Add `selinux.SEBoolean`, `selinux.FileContextMapping`, `selinux.SEPorts`, `selinux.SEPort` facts (@morrison12)
+ Add `snap.package` operation & `snap.SnapPackage`, `snap.SnapPackages` facts (@pabloxio)
+ Add beta `files.block` operation implementation (@morrison12)

Fixed:

+ Include all systemd units in `systemd.SystemdStatus` fact (@mariusmuja)
+ Handle installed RPM packages in `rpm.RpmPackage` fact (@mariusmuja)
+ Fix host loop cycle errors with new `host.loop` method
+ Always use ISO format date in `server.Date` fact, should resolve any outstanding parse errors

Other changes:

+ Fix a whole load of documentation typos (@simonw)
+ Generic typing stub for operation decorator (@mariusmuja)
+ First pass at type annotations for the API (@lowercase00)
+ Add type checking CI job
+ Decomposition of many internal API functions & cleanup (@lowercase00)
+ Use `macos-latest` GitHub runner (@morrison12)
+ Fix documentation URL (@blaisep)

# v2.4

Delayed getting this out, lots of little improvements.

Added:

+ Add `server.user_authorized_keys` operation
+ Add global `_continue_on_error` argument
+ Add `dir_mode` argument to `files.sync` operation (@filips123)
+ Copy local permissions when `mode=True` in `files.put` operation
+ Add `headers` and `insecure` arguments to `files.download` operation

Fixed:

+ Get facts with host & state context (@jaysoffian)
+ Fix short facts with arguments (@jaysoffian)
+ Fix hang on launch of container in `lxd.container` operation (@zachwaite)
+ Run operations with host context
+ Fix idempotency with uploads to a directory in `files.put` operation

Other changes:

+ Fix multiple doc typos (@timgates42)
+ Fix variable typo (@bouke-sf)
+ Fix CLI shell autocomplete doc (@jaysoffian)
+ Implement idempotency in `git.bare_repo` operation
+ Add typing to fact classes
+ Start testing files operations with `pathlib` objects

# v2.3

Relatively small quick release with two additions and a bunch of fixes.

Added:

+ Add `create_home` argument to `server.user` operation
+ Separate no change/change in proposed changes & results output
+ Support IO-like objects as `stdin`

Fixed:

+ Fix short fact gathering
+ Fix handling of IO-like objects when `assume_exists=True` in `files.put` operation
+ Don't fail to ensure user home dir that already exists as a link
+ Rename file utils to avoid clashes/confusion with operations

Internal:

+ Check operation type stubs during CI

# v2.2

The main feature of `2.2` is the switch to **using a DAG to generate operation order**. This mostly replaces line-number ordering (still used to tie-break) and means hacks such as `state.preserve_loop_order` are no longer required!

The second highlight feature is the inclusion of **type stub files for operations** that include all of the global arguments. Thank you to @StefanBRas for implementing this.

Other changes:

+ Use home directory fact for default in `server.user` operation (@yunzheng)
+ Fix matching `replace` as a whole line in `files.line` operation
+ Fix bug in `mysql.privileges` invalid argument requesting `MysqlUserGrants` fact


# v2.1

First `2.x` point release! Major feature: **nested operations** (at last!).

Based on the changes to operations in `2.x` nested operations make it possible to generate & execute operations on the fly at execution time, rather than using the low-level connector API. This unlocks all kinds of complex deploys that were previously impossible or complex to implement. Let's look at an example:

```py
from pyinfra import logger
from pyinfra.operations import python, server

def callback():
    result = server.shell(commands=["echo output"])
    logger.info(f"Got result: {result.stdout}")

python.call(
    name="Execute callback function",
    function=callback,
)
```

Other new stuff:

+ Add `host.reload_fact(...)` - bypasses the fact cache to force reloading of fact data
+ Add `deb.DebArch` fact
+ Add `ssh_paramiko_connect_kwargs` host data used in the `@ssh` connector

Bugfixes:

+ Fix: Remove state/host arguments from apt.dist_upgrade operation (@pabloxio)
+ Fix `files.put` hashing local file that doesn't exist when `assume_exists=True`
+ Fix parsing of link targets in RHEL 6 systems
+ Prefer `zypper` over `apt` when both present in `server.packages` operation

Internal changes:

+ Fix license link (@Lab-Brat)
+ Run `black` and `isort` across the codebase, now part of CI


# v2.0.2

+ Fix for `config.SUDO`/etc handling for operation argument defaults 

# v2.0.1

+ Rewrite & fix/speedup `systemd` facts using `systemctl show`
+ Support passing IO-like objects into `files.template` operation
+ Support `accept-new` SSH config for `StrictHostKeyChecking`
+ Fix hashing of facts with non-keyword arguments
+ Fix connect to non-connected hosts before collecting facts
+ Fix `config.REQUIRE_PYINFRA_VERSION` & `config.REQUIRE_PACKAGES` handling
+ Many little docs improvements

# v2.0

The first `2.x` release! Like v0 -> v1 this release mostly removes legacy APIs and methods which show warnings in v1. Major changes:

Breaking: **Python 2.7 (finally!), 3.5 support dropped**, Python 3.6 is now the minimum required version.

Breaking: **the "deploy directory" concept has been removed** - everything now executes from the current working directory which removes the ambiguous magic v1 used to pick a deploy directory. A new `--chdir` CLI flag has been added to set the working directory before `pyinfra` executes.

This may affect scripts or CI workflows currently setup, for example:

```sh
# Old v1, deploy directory becomes deploys/elasticsearch/
pyinfra deploys/elasticsearch/inventories/production.py deploys/elasticsearch/deploy.py

# New v2, explicit chdir required
pyinfra --chdir deploys/elasticsearch/ inventories/production.py deploy.py
```

**Parallel operation generation & facts rewrite** - this is a huge improvement to how `pyinfra` generates commands to run on target hosts. This is now run in parallel across all hosts. Facts are now collected by individual host rather than across all hosts which may yield significant speedups in certain situations.

This change also brings **support for all of the execution global arguments to facts**, and hugely simplifies the facts implementation. Global arguments will now be read from host data in exactly the same way they are for operations, which was often a confusing gotcha in v1. This also means that the arguments can have different values for each host and this will not cause issues.

**Other breaking changes** (warnings shown in v1 for most):

+ Non-existent host data raises an `AttributeError` when accessed via `host.data.X`
+ Change default `branch` argument to `None` in `git.repo` operation
+ `present` argument removed from `mysql.privileges` operation
+ Config variables must now be set on the global `config` object
+ Old style `host.fact.fact_name` access has been removed
+ The legacy `init.*` operations have been removed
+ Stop lowercasing package names in facts & operations
+ Remove `--facts` and `--operations` CLI flags
+ Remove `--debug-data` CLI flag
+ Remove `Windows` prefix on all Windows facts
+ Rename `name` argument to `path` in `windows_files.*` operations
+ Remove support for jinja2 template parsing in string arguments
+ Remove old `pyinfra.modules` module/import
+ Remove `config.MIN_PYINFRA_VERSION`
+ Remove `branch` and `create_branch` arguments in `git.worktree` operation
+ Remove `touch_periodic` argument in `apt.update` operation (never used)
+ `pyinfra.api.connectors` module moved to `pyinfra.connectors`

**Deprecated** (showing warnings, to be removed in v3):

+ `state` and `host` arguments no longer need to be passed into operation or deploy functions
+ `postgresql_*` arguments renamed to `psql_*` in `postgresql.*` operations & facts

# v1.x

[See this file in the `1.x` branch](https://github.com/Fizzadar/pyinfra/blob/1.x/CHANGELOG.md).
