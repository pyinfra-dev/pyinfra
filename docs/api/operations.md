# Writing Facts & Operations

Operations & facts the building blocks pyinfra uses to make changes to hosts, this document describes how you can write your own to extend pyinfra's functionality.

## Operations

[Operations](../operations) are defined as Python functions. They are passed the current deploy state, the target host and any operation arguments. Operation functions read state from the host, comparing it to the arguments, and yield commands.

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

Operations can also call other operations using ``yield from`` syntax:

```py
yield from files.file(
    path="/some/file",
    ...,
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
def file(name, present=True):
    '''
    Manage the state of files.

    + name: name/path of the remote file
    + present: whether the file should exist
    '''

    info = host.get_fact(File, path=name)

    # Not a file?!
    if info is False:
        raise OperationError("{0} exists and is not a file".format(name))

    # Doesn't exist & we want it
    if info is None and present:
        yield "touch {0}".format(name)

    # It exists and we don't want it
    elif info and not present:
        yield "rm -f {0}".format(name)
```

## Facts

[Facts](../facts) are written as Python classes. They provide a ``command`` (as either a string or method)
and a ``process`` function. The command is executed on the target host and the output
passed (as a ``list`` of lines) to the ``process`` handler to generate fact data. Facts can output anything, normally a ``list`` or ``dict``.

Fact classes may provide a ``default`` function that takes no arguments (except ``self``). The return value of this function is used if an error
occurs during fact collection. Additionally, a ``requires_command`` variable can be set on the fact that specifies a command that must be available
on the host to collect the fact. If this command is not present on the host the fact will be set to the default, or empty if no ``default`` function
is available.

### Importing & Using Facts

Like operations, facts are imported from Python modules and executed by calling `Host.get_fact`. For example:

```py
from pyinfra import host
from pyinfra.facts.server import Which

host.get_fact(Which, command='htop')
```

### Example: getting swap status

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

### Example: getting the list of files in a directory

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

### Example: getting any output from a command

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
