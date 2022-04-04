Deploy Execution
================

``pyinfra`` executes in two main phases: **fact gathering** and **executing operations**. This split is what enables ``pyinfra`` to execute dry runs (``--dry``) and output a "diff" of commands & files (``--debug-operations``) to update a servers state as defined.

**Fact gathering**:
    During this phase information is collected from the remote servers and compared to the desired state defined by the user (ie a file of operations). This phase is **read only** and collects most of the information needed to execute the deploy.

**Executing operations**:
    This phase takes the commands/files/etc generated during fact gathering and executes the commands, uploads the files to the remote system. At the end of the operations the remote state should reflect that defined by the users operations.

This two phase deploy process enables ``pyinfra`` to do some really interesting things, however there are some limitations to consider.


Detailed lifecycle of executing the ``pyinfra`` CLI
---------------------------------------------------

Setup & connect
~~~~~~~~~~~~~~~

+ Parse & validate CLI arguments, inventory file, group data files, commands
+ Create ``Inventory``, ``Config`` and ``State`` objects

  + Populate the inventory with ``Host`` objects for each host
  + Load up any filesystem based config variables

+ Connect to each target host from the inventory using the relevant connector

Fact gathering / operation preparation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

+ Loop through each deploy file:

  + Loop through each host and execute the file
  + As operation functions are called, needed facts are fetched from hosts
  + Commands output by operations are stored in the state

Operation execution
~~~~~~~~~~~~~~~~~~~

+ Generate order of operations

  + Uses line numbers in CLI mode (ie - works like the user would expect)
  + Uses `add_op` call order in API mode

+ Loop through each operation

  + For each host, execute the commands specific for this (op, host) pair
  + Collect results and trigger failure handling for any errors encountered
  + Store the results in the state

Completion
~~~~~~~~~~

+ Disconnect from all the target hosts
+ Write out the results to the user


Limitations
-----------

Interdependent operations
~~~~~~~~~~~~~~~~~~~~~~~~~

The major disadvantage to separating the deploy into two phases comes into effect where operations rely on each other - i.e. the changes of one operation will affect a later operations facts. Consider the following example:

.. code:: python

    from pyinfra.operations import apt, files

    apt.packages(
        {'Install nginx'},
        'nginx',
    )

    files.link(
        {'Remove default nginx site'},
        '/etc/nginx/sites-enabled/default',
        present=False,
    )

This is problematic because the link, ``/etc/nginx/sites-enabled/default``, won't exist during the first phase as it is created by the previous ``apt.packages`` operation. This means, on first run, the second operation will do nothing, leaving the link in place. Re-running the deploy would correct this, but we can also provide hints to ``pyinfra`` in such cases, i.e.:

.. code:: python

    from pyinfra.operations import apt, files

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

The addition of ``assume_present`` will force ``pyinfra`` to remove the file without checking if it exists first.

Dynamic operations
~~~~~~~~~~~~~~~~~~

Sometimes it is impossible to know all the facts before executing operations. For example the unique identifier for the server that a package generates, which happens inside an operation. This requires reading this state (the identifier) from the server *during* the deploy.

See the :doc:`./examples/dynamic_execution_deploy` example.

Loops
~~~~~

In CLI mode ``pyinfra`` uses *line numbers* to determine the order in which operations are executed. While this is very effective and executing in an order users would expect, loops are an exception. ``pyinfra`` inclues a workaround for this with the ``state.preserve_loop_order`` function:

.. code:: python

    # list of items
    items = ['a', 'b', 'c']

    # This loop will be executed as:
    # > item: a
    # > item: b
    # > item: c
    # > end item: a
    # > end item: b
    # > end item: c
    for item in items:
        server.shell({'item: {0}'.format(item)}, 'hi')
        server.shell({'end item: {0}'.format(item)}, 'hi')


    # This loop will be executed as:
    # > item: a
    # > end item: a
    # > item: b
    # > end item: b
    # > item: c
    # > end item: c
    with state.preserve_loop_order(items) as loop_items:
        for item in loop_items():
            server.shell({'item: {0}'.format(item)}, 'hi')
            server.shell({'end item: {0}'.format(item)}, 'hi')


Deploy State
------------

At the center of a ``pyinfra`` deployment is a state object. This object holds the inventory of hosts and data, operations to execute and status of the execution.

+ All hosts (or those matching the ``-limit``) are connected to and flagged as both **activated** and **active**.
+ Deploy files and/or operations are loaded for every activated host, any additional hosts are connected to as required (to collect facts, for example).
+ Proposed operations, along with the number of commands for each hosts, are shown to the user for every **activated** host. At this point if the ``--dry`` flag is passed, ``pyinfra`` stops.
+ Operations begin to execute, when hosts fail they are flagged as no longer **active**, ``pyinfra`` checks **active** vs **activated** counts to determine if we break the ``FAIL_PERCENT``, and bail the whole deploy if so.
+ Finally the resulting state is printing to the user for every **activated** host.
