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
