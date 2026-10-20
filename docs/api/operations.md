# Writing Operations

[Operations](../operations) are defined as Python functions. They are passed the current deploy state, the target host, and any operation arguments. Operation functions read state from the host, compare it to the arguments, and yield commands.

## Input: arguments

Operations can accept any arguments except ``name`` and those starting with ``_`` which are reserved for internal use.

```py
@operation()
def my_operation(...):
    ...
```

## Output: commands

Operations are generator functions and ``yield`` three types of command:

```py
# Shell commands, simply represented by a string OR the `StringCommand` class
yield StringCommand("echo", "Shell!")

# File uploads represented by the `FileUploadCommand` class
yield FileUploadCommand(filename_or_io, remote_filename)

# File downloads represented by the `FileDownloadCommand` class
yield FileDownloadCommand(remote_filename, filename_or_io)

# Python functions represented by the `FunctionCommand` class
yield FunctionCommand(function, args_list, kwargs_dict)

# Additionally, commands can override most global arguments
yield StringCommand("echo", "Shell!", _sudo=True)
```

Operations can also call other operations using ``yield from <operation>._inner`` syntax.
```py
yield from files.file._inner(
    path="/some/file",
    ...,

    # Only arguments for the operation itself are allowed, global arguments
    # such as e.g. _sudo are not accepted.
)
```

## Example: managing files

This is a simplified version of the ``files.file`` operation, which will create/remove a
remote file based on the ``present`` kwargs:

```py
from pyinfra import host
from pyinfra.api import OperationError, QuoteString, StringCommand, operation
from pyinfra.facts.files import File

@operation()
def file(path: str, present: bool = True):
    '''
    Manage the state of files.

    + path: name/path of the remote file
    + present: whether the file should exist
    '''

    info = host.get_fact(File, path=path)

    # Path exists but isn't a regular file
    if info is False:
        raise OperationError(f"{path} exists and is not a file")

    # Doesn't exist & we want it
    if info is None and present:
        yield StringCommand("touch", QuoteString(path))

    # It exists and we don't want it
    elif info and not present:
        yield StringCommand("rm", "-f", QuoteString(path))
```

!!! warning "Compose shell commands with `StringCommand` and `QuoteString`"
    Never build shell commands with plain string formatting or f-strings that include user-supplied values — that opens you to shell injection. Wrap every interpolated argument in `QuoteString` (paths, names, even integers) and combine the parts with `StringCommand`. See [`pyinfra.api.command`](reference.md) for the full set of command primitives.

!!! note "Contributing an operation to pyinfra itself?"
    Operations shipped in the pyinfra repo must also be registered in `pyinfra-metadata.toml` at the repo root (with a `type = "operation"` entry and one or more tags). Omitting it won't break the operation at runtime, but the docs site won't pick it up. This only applies to in-tree contributions; external pyinfra packages don't need this file.
