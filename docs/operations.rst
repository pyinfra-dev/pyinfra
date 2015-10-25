Operations
==========

Operations are the lifeblood of pyinfra, they are namespaced as :doc:`modules/index` and are used to define the desired state of target servers. When called, they use :doc:`facts` to determine the difference between actual and desired state. This diff is used to generate the required commands & file changes needed to align the server with our defined state.

Using an operation in a deploy script is just like standard Python:

.. code:: python

    from pyinfra.modules import server

    server.user(
        'my_user',
        home='/home/my_users_custom_home',
        shell='/bin/bash'
    )

Running order
-------------

By default operations are run sequentially and, unless `ignore_errors=True`, will stop at the first failure. Although they are sequential, if an operation has multiple hosts to run on, this will be done in parallel (unless `--serial` is passed to pyinfra).

It is also possible to run without waiting on all the hosts at each operation (resulting in non-sequential changes accross hosts) by adding the `--nowait` flag. This is useful for maintenance tasks which don't require each host to correctly update a git repository before running an update, for example. In this case, when there is an error, only the host affected will stop, while all the others continue.
