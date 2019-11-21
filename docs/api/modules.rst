Writing Modules
===============

At the core of pyinfra lie facts and operations. These are namespaced as different
modules. This guide should help you get started writing both operations and facts.


Operations
----------

Operations are, in general, simple Python functions. They are passed the current deploy
state and a target host, along with any operation arguments. The function reads state
from the host, comparing it to the arguments, and yields **commands**.

Input: reserved arguments
~~~~~~~~~~~~~~~~~~~~~~~~~

The following keyword arguments are reserved for controlling how operations deploy, and
cannot be used within operations: ``sudo``, ``sudo_user``, ``ignore_errors``, ``serial``,
``run_once``, ``timeout``, ``env``, ``name``, ``op``, ``get_pty``. In addition to this,
the *first* argument cannot accept ``set`` objects, as these will be removed for use as
the operation name.

Output: commands
~~~~~~~~~~~~~~~~

Operations are generator functions and ``yield`` three types of command:

.. code:: python

    # Shell commands, simply represented by a string
    yield 'echo "Shell!"'

    # File uploads represented by a tuple with where the first item is 'upload'
    yield ('upload', filename_or_io, remote_filename)

    # File downloads represented by a tuple with where the first item is 'download'
    yield ('download', filename_or_io, remote_filename)

    # Python functions represented by a tuple where the first item is a function
    yield (function, args_list, kwargs_dict)

    # Additionally, commands can be wrapped in a dict, overriding sudo/sudo_user
    yield {
        'command': 'echo "Shell!"',
        'sudo': True
    }

Example: managing files
~~~~~~~~~~~~~~~~~~~~~~~

This is a simplified version of the ``files.file`` operation, which will create/remove a
remote file based on the ``present`` kwargs:

.. code:: python

    from pyinfra.api import operation

    @operation
    def file(state, host, name, present=True):
        '''
        Manage the state of files.

        + name: name/path of the remote file
        + present: whether the file should exist
        '''

        info = host.fact.file(name)

        # Not a file?!
        if info is False:
            raise OperationError('{0} exists and is not a file'.format(name))

        # Doesn't exist & we want it
        if info is None and present:
            yield 'touch {0}'.format(name)

        # It exists and we don't want it
        elif info and not present:
            yield 'rm -f {0}'.format(name)


Facts
-----

Facts are written as Python classes. They provide a ``command`` (as a string or method)
and a ``process`` function. The command is executed on the target host and the output
passed (as a ``list`` of lines) to the ``process`` handler to generate fact data.

Facts can output any data structure, normally a ``list`` or ``dict``. They often make
heavy use of regex to parse the output.

Example: getting the sha1 of a file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This fact returns a list of files found in a given directory.

.. code:: python

    from pyinfra.api import FactBase

    class FindFiles(FactBase):
        '''
        Returns a list of files from a start point, recursively using find.
        '''

        def command(self, name):
            # Find files in the given location
            return 'find {0} -type f'.format(name)

        def process(self, output):
            # Return the list of lines (files) as-is
            return output
