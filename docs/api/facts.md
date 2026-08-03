# Writing Facts

[Facts](../facts) are written as Python classes. They provide a ``command`` (as either a string or method)
and a ``process`` function. The command is executed on the target host and the output
passed (as a ``list`` of lines) to the ``process`` handler to generate fact data. Facts can output anything, normally a ``list`` or ``dict``.

Fact classes may provide a ``default`` function that takes no arguments (except ``self``). The return value of this function is used if an error
occurs during fact collection.

## `FactBase` vs `ShortFactBase`

There are two base classes for facts and they solve different problems:

- **`FactBase`** — defines a *new* fact that runs a shell command on the host and parses the output. Use this whenever you need information that isn't already available from an existing fact.
- **`ShortFactBase`** — defines a *derived* view over an existing fact. It does not run any command on the host; instead it points at another fact via a `fact` class attribute and post-processes that fact's result. Use this when you want a simpler or different shape of an existing fact (e.g. just one field from a dict). Both facts share the same cached command result, so adding a `ShortFactBase` costs nothing at runtime.

For example, `LinuxName` is a `ShortFactBase` that extracts the `name` field from the larger `LinuxDistribution` fact:

```py
from typing_extensions import override
from pyinfra.api import ShortFactBase

class LinuxName(ShortFactBase[str]):
    """
    Returns the name of the Linux distribution. Shortcut for
    ``host.get_fact(LinuxDistribution)['name']``.
    """

    fact = LinuxDistribution

    @override
    def process_data(self, data) -> str:
        return data["name"]
```

The rest of this page covers `FactBase`.

## Guarding against missing binaries: `requires_command`

Override `requires_command` to declare a binary that must be present on the remote host before
the fact command is run. When the binary is absent pyinfra emits a unique sentinel instead of
executing the command, then raises `MissingCommandError` internally:

```py
from pyinfra.api import FactBase

class ZfsPools(FactBase):
    def requires_command(self) -> str:
        return "zpool"

    def command(self) -> str:
        return "zpool get -H all"
```

**Phase-aware behaviour** — The exception is handled differently depending on the deploy phase:

- **Prepare phase**: the fact returns `default()` silently. The binary may simply not be
  installed yet; a later operation will install it.
- **Execute phase** (v3): a warning is logged and `default()` is returned. This preserves
  backwards compatibility for deploys that rely on `default()` being returned when a binary
  is absent.
- **Execute phase** (v4): `MissingCommandError` will be raised so the developer knows the
  deploy is incorrectly ordered (the install step must come first).

## Checking runtime prerequisites: `check_preconditions()`

Some facts require more than just a binary — they need a specific runtime state (e.g. a kernel
module loaded, a service running). Override `check_preconditions` to express these checks:

```py
from pyinfra.api import FactBase

class ZfsDatasets(FactBase):
    def requires_command(self) -> str:
        return "zfs"

    def check_preconditions(self, state, host):
        from pyinfra.facts.server import KernelModules
        modules = host.get_fact(KernelModules) or {}
        if "zfs" not in modules:
            return "kernel module 'zfs' is not loaded"

    def command(self) -> str:
        return "zfs get -H all"
```

Return values:

| Return value | Meaning |
|---|---|
| `None` (or no return) | Prerequisites satisfied — proceed normally |
| `"reason"` | Prerequisite not satisfied with a human-readable explanation |

The framework raises `FactPreconditionError` automatically and applies the same
phase-aware behaviour as `requires_command`: silent during prepare, raised during execute.
Fact authors never need to import any exception class.

## Exception hierarchy

All "fact skipped" situations use a common base class so callers can catch at any level:

```
FactError
└── FactNotCollected          # base: fact could not be collected
    ├── MissingCommandError   # requires_command binary absent
    └── FactPreconditionError # check_preconditions() not satisfied
```

All three are exported from `pyinfra.api`.

## Importing & Using Facts

Like operations, facts are imported from Python modules and executed by calling `Host.get_fact`. For example:

```py
from pyinfra import host
from pyinfra.facts.server import Which

host.get_fact(Which, command='htop')
```

## Example: getting swap status

This fact returns a boolean indicating whether swap is enabled. For this fact the ``command`` is declared as a class attribute.

```py
from  pyinfra.api import FactBase

class SwapEnabled(FactBase):
    '''
    Returns a boolean indicating whether swap is enabled.
    '''

    command = 'swapon --show'

    def process(self, output):
        return len(output) > 0  # we have one+ lines
```

This fact could then be used like so:

```py
is_swap_enabled = host.get_fact(SwapEnabled)
```

## Example: getting the list of files in a directory

This fact returns a list of files found in a given directory. For this fact the ``command`` is declared as a class method, indicating the fact takes arguments.

```py
from pyinfra.api import FactBase

class FindFiles(FactBase):
    '''
    Returns a list of files from a start point, recursively using find.
    '''

    def command(self, path):
        # Find files in the given location
        return 'find {0} -type f'.format(path)

    def process(self, output):
        return output  # return the list of lines (files) as-is
```

This fact could then be used like so:

```py
list_of_files = host.get_fact(FindFiles, path='/somewhere')
```

## Example: getting any output from a command

This fact returns the raw output of any command. For this fact the ``command`` is declared as a class method, indicating the fact takes arguments.

```py
from pyinfra.api import FactBase

class RawCommandOutput(FactBase):
    '''
    Returns the raw output of a command.
    '''

    def command(self, command):
        return command

    def process(self, output):
        return '\n'.join(output)  # re-join and return the output lines
```

This fact could then be used like so:

```py
command_output = host.get_fact(RawCommandOutput, command='execute this command')
```

!!! note "Contributing a fact to pyinfra itself?"
    Facts shipped in the pyinfra repo must also be registered in `pyinfra-metadata.toml` at the repo root (with a `type = "fact"` entry and one or more tags). Omitting it won't break the fact at runtime, but the docs site won't pick it up. This only applies to in-tree contributions; external pyinfra packages don't need this file.
