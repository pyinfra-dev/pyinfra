Writing Operations
==================

:doc:`Operations <../operations>` are defined as Python functions. They are passed the current deploy state, the target host and any operation arguments. Operation functions read state from the host, comparing it to the arguments, and yield **commands**.

Input: arguments
~~~~~~~~~~~~~~~~

Operations can accept any arguments except ``name`` and those starting with ``_`` which are reserved for internal use.

.. code:: python

    @operation()
    def my_operation(...):
        ...

Output: commands
~~~~~~~~~~~~~~~~

Operations are generator functions and ``yield`` three types of command:

.. code:: python

    # Shell commands, simply represented by a string OR the `StringCommand` class
    yield "echo 'Shell!'"
    yield StringCommand("echo 'Shell!'")

    # File uploads represented by the `FileUploadCommand` class
    yield FileUploadCommand(filename_or_io, remote_filename)

    # File downloads represented by the `FileDownloadCommand` class
    yield FileDownloadCommand(remote_filename, filename_or_io)

    # Python functions represented by the `FunctionCommand` class
    yield FunctionCommand(function, args_list, kwargs_dict)

    # Additionally, commands can override some of the global arguments
    yield StringCommand("echo 'Shell!'", sudo=True)

Operations can also call other operations using ``yield from`` syntax:

.. code:: python

    yield from files.file(
        path="/some/file",
        ...,
    )

Example: managing files
~~~~~~~~~~~~~~~~~~~~~~~

This is a simplified version of the ``files.file`` operation, which will create/remove a
remote file based on the ``present`` kwargs:

.. code:: python

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
