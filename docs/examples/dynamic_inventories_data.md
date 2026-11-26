---
orphan: true
---
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

## Test Inventories with Fake Data

For tests, demos and screenshots you often want a whole inventory of hosts
without any real target to connect to. The built-in [`@fake` connector](../connectors/fake.md)
simulates command execution locally without running anything, and pairs nicely
with a [function-based inventory](../inventory-data.md#function-based-inventories-alpha)
to generate any number of fake hosts and data in plain Python:

```py
# inventory.py

def make_test(web_count=2, db_count=1):
    web_hosts = [f'@fake/web-{i}' for i in range(1, web_count + 1)]
    db_hosts = [f'@fake/db-{i}' for i in range(1, db_count + 1)]

    # Any host can script specific command results (including failures) via
    # `fake_responses`; anything unmatched just succeeds with no output.
    web_hosts[0] = (
        '@fake/web-1',
        {
            'fake_responses': {
                'git --version': 'git version 2.40.0',
                'pip install': {
                    'success': False,
                    'stderr': 'error: externally-managed-environment',
                },
            },
        },
    )

    return {
        'web': (web_hosts, {'role': 'web', 'port': 80}),
        'db': (db_hosts, {'role': 'db', 'port': 5432}),
    }
```

Point pyinfra at the function on the command line as `module.attribute`:

```sh
# Inspect the generated hosts and data
pyinfra inventory:make_test debug-inventory

# Run any command or operation against the fake hosts
pyinfra inventory:make_test exec -- echo "hello world"

# `@fake/web-1` reports the scripted failure, the rest succeed
pyinfra inventory:make_test server.shell "pip install requests"
```

See the [`@fake` connector](../connectors/fake.md) documentation for the full
`fake_responses` format (substring and regular-expression matchers), simulated
command timing and other available data.
