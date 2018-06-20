Using Python
============

.. warning::

    This page describes the limitations of the pyinfra **CLI**. This applies to any Python files used to describe operations (the deploy code), eg ``deploy.py`` or ``tasks/nginx.py``. pyinfra will display a warning if any issues are detected and ensures that operations are always executed in order **per host** so there's no risk of, say, trying to use ``docker`` before installing it.

The ``pyinfra`` CLI reads operations from normal Python files by executing the file once per host in the inventory. This means that pyinfra has to hash the arguments of a given operation so they can be grouped together. This means that:

    **When executed, the Python code in the files must execute the same number of operations, each with similar arguments.**

Practically speaking, this means there are a few differences from how you would normally write Python code:


String Formatting
-----------------

.. code:: python

    # This will generate a new operation per host where `host.data.filename` changes:

    files.template(
        '/opt/{0}'.format(host.data.filename),
        ...
    )

    # Which should be re-written using jinja2 style strings:

    files.template(
        '/opt/{{ host.data.filename }}',
        ...
    )


Loops
-----

.. code:: python

    # Loops must be the same for all hosts, ie `host.data.commands` in:

    for command in host.data.commands:
        server.shell(command)

    # Where the data will change between hosts, it must be passed in as an operation keyword
    # argument. There is currently no `state.X` workaround for this.

    server.shell(
        host.data.commands,
        ...
    )


Code Formatting
---------------

It is important to maintain a difference between pyinfra code, with it's limitations above, and "pure" Python (especially true if your application is written in Python). As such, it is highly recommended to use the spaced out formatting used in this documentation:

.. code:: python

    # Define operation calls as a "block"
    files.put(
        # Always provide a description of the operation
        {'Upload a file'},

        # Split operation arguments onto different lines
        '/home/nick/myfile.txt',
        '/home/{{ host.data.user }}/myfile.txt',

        # Provide global arguments last
        sudo=True,
    )
