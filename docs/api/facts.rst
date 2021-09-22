Writing Facts
=============

:doc:`Facts <../facts>` are written as Python classes. They provide a ``command`` (as either a string or method)
and a ``process`` function. The command is executed on the target host and the output
passed (as a ``list`` of lines) to the ``process`` handler to generate fact data. Facts can output anything, normally a ``list`` or ``dict``.

Fact classes may provide a ``default`` function that takes no arguments (except ``self``). The return value of this function is used if an error
occurs during fact collection. Additionally, a ``requires_command`` variable can be set on the fact that specifies a command that must be available
on the host to collect the fact. If this command is not present on the host the fact will be set to the default, or empty if no ``default`` function
is available.

Importing & Using Facts
~~~~~~~~~~~~~~~~~~~~~~~

Like operations, facts are imported from Python modules and executed by calling `Host.get_fact`. For example:

.. code:: python

    from pyinfra import host
    from pyinfra.facts.server import Which

    host.get_fact(Which, command='htop')


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

    is_swap_enabled = host.get_fact(SwapEnabled)


Example: getting the list of files in a directory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This fact returns a list of files found in a given directory. For this fact the ``command`` is delcated as a class method, indicating the fact takes arguments.

.. code:: python

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

This fact could then be used like so:

.. code:: python

    list_of_files = host.get_fact(FindFiles, path='/somewhere')


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

    command_output = host.get_fact(RawCommandOutput, command='execute this command')
