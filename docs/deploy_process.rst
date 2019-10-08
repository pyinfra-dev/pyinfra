Executing Deploys
=================

pyinfra executes in two main phases: **fact gathering** and **executing operations**. This split is what enables pyinfra to execute dry runs (``--dry``) and output a "diff" of commands & files (``--debug-operations``) to update a servers state as defined.

**Fact gathering**:
    During this phase information is collected from the remote servers and compared to the desired state defined by the user (ie a file of operations). This phase is **read only** and collects most of the information needed to execute the deploy.

**Executing operations**:
    This phase takes the commands/files/etc generated during fact gathering and executes the commands, uploads the files to the remote system. At the end of the operations the remote state should reflect that defined by the users operations.

This two phase deploy process enables pyinfra to do some really interesting things, however there are some limitations to consider.


Limitations
-----------

Interdependent operations
~~~~~~~~~~~~~~~~~~~~~~~~~

The major disadvantage to separating the deploy into two phases comes into effect where operations rely on each other - ie the changes of one operation will affect a later operations facts. Consider the following example:

.. code:: python

    from pyinfra.modules import apt, files

    apt.packages(
        {'Install nginx'},
        'nginx',
    )

    files.link(
        {'Remove default nginx site'},
        '/etc/nginx/sites-enabled/default',
        present=False,
    )

This is problematic because the link, ``/etc/nginx/sites-enabled/default``, won't exist during the first phase as it is created by the previous ``apt.packages`` operation. This means, on first run, the second operation will do nothing, leaving the link in place. Re-running the deploy would correct this, but we can also provide hints to pyinfra in such cases, ie:

.. code:: python

    from pyinfra.modules import apt, files

    install_nginx = apt.packages(
        {'Install nginx'},
        'nginx',
    )

    files.link(
        {'Remove default nginx site'},
        '/etc/nginx/sites-enabled/default',
        present=False,
        assume_present=install_nginx.changed,
    )

The addition of ``assume_present`` will force pyinfra to remove the file without checking if it exists first.

Dynamic operations
~~~~~~~~~~~~~~~~~~

Sometimes it is impossible to know all the facts before executing operations. For example the unique identifier for the server that a package generates, which happens inside an operation. This requires reading this state (the identifier) from the server *during* the deploy.

See the :doc:`./examples/dynamic_execution_deploy` example.
