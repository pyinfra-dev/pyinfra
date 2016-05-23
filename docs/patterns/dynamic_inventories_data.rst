Dynamic Inventories & Data
==========================

One of the biggest features of pyinfra is that it's configured in regular Python. This
means inventory, data and deploy files can use Python code and modules. As a result it is
possible to generate inventory and group data for a deploy.

For example, here we fetch the list of target hosts from some internal inventory API:

.. code:: python

    # inventory.py

    import requests

    DB_SERVERS = []
    WEB_SERVERS = []

    servers = requests.get('inventory.mycompany.net/api/v1/app_servers').json()

    for server in servers:
        if server['group'] == 'db':
            DB_SERVERS.append(server['hostname'])

        elif server['group'] == 'web':
            WEB_SERVERS.append(server['hostname'])


Like the dynamic inventory, we can use Python inside group data. It is also possible to
access the initial inventory (without group data):

.. code:: python

    # group_data/all.py

    from pyinfra import inventory

    master_db_server = inventory.db_servers[0].name
