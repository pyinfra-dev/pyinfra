# Dynamic Inventories & Data

One of the biggest features of pyinfra is that it's configured in regular Python. This means inventory, data and deploy files can use Python code and modules. As a result it is possible to generate inventory and group data for a deploy.

For example, here we fetch the list of target hosts from some internal inventory API:

```py
# inventory.py

import requests

def get_servers():
    db = []
    web = []

    servers = requests.get('inventory.mycompany.net/api/v1/app_servers').json()

    for server in servers:
        if server['group'] == 'db':
            db.append(server['hostname'])

        elif server['group'] == 'web':
            web.append(server['hostname'])

    return db, web


db_servers, web_servers = get_servers()
```

Like the dynamic inventory, we can use Python inside group data. It is also possible to access the initial inventory (without group data):

```py
# group_data/all.py

from pyinfra import inventory

master_db_server = inventory.db_servers[0].name
```

```py
# group_data/web_servers.py

db_user = 'username'
```
