# Writing Operations

[Operations](../operations) are defined as Python functions. They are passed the current deploy state, the target host, and any operation arguments. Operation functions read state from the host, compare it to the arguments, and yield commands.

### Input: arguments

Operations can accept any arguments except ``name`` and those starting with ``_`` which are reserved for internal use.

```py
@operation()
def my_operation(...):
    ...
```

### Output: commands

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

### Example: managing files

This is a simplified version of the ``files.file`` operation, which will create/remove a
remote file based on the ``present`` kwargs:

```py
from pyinfra import host
from pyinfra.api import operation
from pyinfra.facts.files import File

@operation()
def file(path, present=True):
    '''
    Manage the state of files.

    + path: name/path of the remote file
    + present: whether the file should exist
    '''

    info = host.get_fact(File, path=path)

    # Not a file?!
    if info is False:
        raise OperationError("{0} exists and is not a file".format(path))

    # Doesn't exist & we want it
    if info is None and present:
        yield "touch {0}".format(path)

    # It exists and we don't want it
    elif info and not present:
        yield "rm -f {0}".format(path)
```
