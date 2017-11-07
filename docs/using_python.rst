Using Python
============

One of the most powerful features of pyinfra is that deploys are configured/written in pure Python. Where possible pyinfra stays out of the way and lets you use the full power of Python to your advantage - however there are a few caveats that this page explains.


String Formatting
-----------------

pyinfra supports jinja2 style string arguments, which should be used over Python's builtin string formatting where you expect the final string to change per host. This is because pyinfra groups operations by their arguments. For example:

.. code:: python

    from pyinfra import host
    from pyinfra.modules import server

    server.user(
        {'Setup the app user'},
        host.data.app_user,
        '/opt/{{ host.data.app_dir }}', # for multiple values of host.data.app_dir we still
                                        # generate a single operation
    )


Conditional Branches
--------------------

pyinfra works by calling the deploy code you write once for each host. This means different conditional branches (``if`` statements, etc) may execute differently for each host. This means that operations may be added, and therefor execute, in a different order to the deploy code.

To avoid these issues, pyinfra provides a global ``when`` keyword argument in all operations and a ``state.when`` context processor for blocks of code:

.. code:: python

    from pyinfra import host, state
    from pyinfra.modules import server

    # Replace if blocks with the state.when context
    with state.when(host.name == 'my-host.net'):
        server.shell('echo "my-host.net op!"')
        ...

    # Use the when kwarg to achieve the same, for single operations
    server.shell(
        'echo "my-host.net op!"',
        when=host.name == 'my-host.net',
    )

pyinfra also has a global ``limit`` keyword argument and a matching ``state.limit`` context processor for blocks:

.. code:: python

    from pyinfra import inventory, state

    with state.limit(inventory.get_host('my-host.net')):
        server.shell('echo "my-host.net op!"')
        ...

    server.shell(
        'echo "my-host.net op!"',
        limit=inventory.get_host('my-host.net'),
    )

.. note::
    Despite the above, pyinfra always ensures that operations are always executed in order **per host** so there's no risk of, say, trying to use ``docker`` before installing it.
