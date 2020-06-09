Writing Facts
=============

Facts are written as Python classes. They provide a ``command`` (as a string or method)
and a ``process`` function. The command is executed on the target host and the output
passed (as a ``list`` of lines) to the ``process`` handler to generate fact data.

Facts can output any data structure, normally a ``list`` or ``dict``. They often make
heavy use of regex to parse the output.

Example: getting the list of files in a directory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
