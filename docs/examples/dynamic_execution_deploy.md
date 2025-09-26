# Dynamic Execution during Deploy

**Note:** this example is out of date (the code is valid, but there's better ways to do it), please see [using operations: operation output & callbacks](/using-operations).

pyinfra is designed around the idea of defining the end-state _before_ executing any changes on the remote server. Generally this works well but sometimes you need the output of one command to feed into another. This can be achieved by executing Python functions mid-deploy.

In this example we install a service (ZeroTier) that generates a random ID for the remote host. We then use this ID to authenticate the server with the ZeroTier API.

```py
import requests

from pyinfra.operations import apt, python, server

# Assumes the repo is configured/apt is updated
apt.packages(
    name='Install ZeroTier',
    packages=['zerotier-one'],
)

def authorize_server(state, host):
    # Run a command on the server and collect status and command output
    status, output = host.run_shell_command('cat /var/lib/zerotier-one/identity.public')
    assert status is True  # ensure the command executed OK

    # First line of stdout is the identity
    server_id = output.stdout_lines[0]

    # Authorize via the ZeroTier API
    response = requests.post('https://my.zerotier.com/.../{0}'.format(server_id))
    response.raise_for_status()

python.call(
    name='Authorize the server on ZeroTier',
    function=authorize_server,
)

server.shell(
    name='Execute some shell',
    commands=['echo "back to other operations!"'],
)
```
