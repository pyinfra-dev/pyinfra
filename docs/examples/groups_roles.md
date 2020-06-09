# Groups & Roles

Deploying complex projects usually involves multiple groups of servers, for example database & web servers. It is useful to separate the deploy into multiple files.

These can be included within deploys using the ``pyinfra.local`` module. A list of hosts can be passed in to limit the include to those hosts.

```py
# deploy.py

from pyinfra import host, local
from pyinfra.operations import server

# Include the web role for the web group
if 'web_servers' in host.groups:
    local.include('tasks/web.py')

# And the same for the database role
if 'db_servers' in host.groups:
    local.include('tasks/database.py')

# This operation runs on all the hosts
server.shell('Runs everywhere')
```

```py
# inventory.py

web_servers = ['web1', 'web2', 'web3']
db_servers = ['db1', 'db2', 'db3']
```

```py
# tasks/web.py

from pyinfra.operations import server

server.shell('install webserver')
...
```

```py
# tasks/database.py

from pyinfra.operations import server

server.shell('install dbserver')
...
```
