Writing Operations
==================

Operations are, in general, simple Python functions. They are passed the current deploy
state and a target host, along with any operation arguments. The function reads state
from the host, comparing it to the arguments, and outputs a list of **commands**.


Input: reserved arguments
-------------------------

The following keyword arguments are reserved for controlling how operations deploy, and
cannot be used within operations: ``sudo``, ``sudo_user``, ``ignore_errors``, ``serial``,
``run_once``, ``timeout``, ``env``, ``name``, ``op``. In addition to this, the *first*
argument cannot accept ``set`` objects, as these will be removed for use as the operation
name.


Output: commands
----------------

Commands come in three forms:

.. code:: python

    # Shell commands, simply represented by a string
    commands.append('echo "Shell!"')

    # File uploads represented by a tuple
    commands.append((file_io_object, remote_filename))

    # Python functions represented by a tuple
    commands.append((function, args_list, kwargs_dict))

    # Additionally, commands can be wrapped in a dict, overriding sudo/sudo_user
    commands.append({
        'command': 'echo "Shell!"',
        'sudo': True
    })


Example: managing files
-----------------------

This is a simplified version of the ``files.file`` operation, which will create/remove a
remote file based on the ``present`` kwargs:

.. code:: python

    @operation
    def file(state, host, name, present=True):
        '''
        Manage the state of files.

        + name: name/path of the remote file
        + present: whether the file should exist
        '''

        info = host.fact.file(name)
        commands = []

        # Not a file?!
        if info is False:
            raise OperationError('{0} exists and is not a file'.format(name))

        # Doesn't exist & we want it
        if info is None and present:
            commands.append('touch {0}'.format(name))

        # It exists and we don't want it
        elif info and not present:
            commands.append('rm -f {0}'.format(name))

        return commands
