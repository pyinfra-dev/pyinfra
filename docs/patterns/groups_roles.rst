Groups & Roles
==============

Deploying complex projects usually involves multiple groups of servers, for example database & web servers. It is useful to separate the deploy into multiple files.

These can be included within deploys using the ``pyinfra.local`` module. A list of hosts can be passed in to limit the include to those hosts.

.. code:: python

    # deploy.py

    from pyinfra import local, inventory

    # Include the web role, targeted at the web group
    local.include(
        'tasks/web.py',
        hosts=inventory.web_servers
    )

    # And the same for the database role & servers
    local.include(
        'tasks/database.py',
        hosts=inventory.db_servers
    )

    # This operation runs on all the hosts
    server.shell('Runs everywhere')

.. code:: python

    # inventory.py

    web_servers = ['web1', 'web2', 'web3']
    db_servers = ['db1', 'db2', 'db3']

.. code:: python

    # tasks/web.py

    server.shell('install webserver')
    ...

.. code:: python

    # tasks/database.py

    server.shell('install dbserver')
    ...
