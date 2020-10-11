Writing Facts
=============

:doc:`Facts <../facts>` are written as Python classes. They provide a ``command`` (as either a string or method)
and a ``process`` function. The command is executed on the target host and the output
passed (as a ``list`` of lines) to the ``process`` handler to generate fact data.

Facts can output any data structure, normally a ``list`` or ``dict``.


Example: getting swap status
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This fact returns a boolean indicating whether swap is enabled. For this fact the ``command`` is declared as a class attribute.

.. code:: python

    from  pyinfra.api import FactBase

    class SwapEnabled(FactBase):
        '''
        Returns a boolean indicating whether swap is enabled.
        '''

        command = 'swapon --show'

        def process(self, output):
            return len(output) > 0  # we have one+ lines

This fact could then be used like so:

.. code:: python

    is_swap_enabled = host.fact.swap_enabled


Example: getting the list of files in a directory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This fact returns a list of files found in a given directory. For this fact the ``command`` is delcated as a class method, indicating the fact takes arguments.

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
            return output  # return the list of lines (files) as-is

This fact could then be used like so:

.. code:: python

    list_of_files = host.fact.find_files('/some/path')


Example: getting any output from a command
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This fact returns the raw output of any command. For this fact the ``command`` is delcated as a class method, indicating the fact takes arguments.

.. code:: python

    from pyinfra.api import FactBase

    class RawCommandOutput(FactBase):
        '''
        Returns the raw output of a command.
        '''

        def command(self, command):
            return command

        def process(self, output):
            return '\n'.join(output)  # re-join and return the output lines

This fact could then be used like so:

.. code:: python

    command_output = host.fact.raw_command_output('execute my command')
