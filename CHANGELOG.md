# v2.0rc1

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
+ `present` argument removed from `mysql.privileges` operation
+ Config variables must now be set on the global `config` object
+ Old style `host.fact.fact_name` access has been removed
+ The legacy `init.*` operations have been removed
+ `--facts` and `--operations` CLI flags/modes removed
+ Remove `--debug-data` CLI flag
+ Remove `Windows` prefix on all Windows facts
+ Rename `name` argument to `path` in `windows_files.*` operations
+ Remove support for jinja2 template parsing in string arguments
+ Remove old `pyinfra.modules` module/import
+ Remove `config.MIN_PYINFRA_VERSION`
+ Remove `branch` and `create_branch` arguments in `git.worktree` operation
+ `pyinfra.api.connectors` module moved to `pyinfra.connectors`
+ Stop lowercasing package names in facts & operations

**Deprecated** (showing warnings, to be removed in v3):

+ `state` and `host` arguments no longer need to be passed into operation or deploy functions
+ `postgresql_*` arguments renamed to `psql_*` in `postgresql.*` operations & facts

# v1.x

[See this file in the `1.x` branch](https://github.com/Fizzadar/pyinfra/blob/1.x/CHANGELOG.md).
