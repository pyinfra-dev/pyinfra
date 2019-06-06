# Dynamic Execution during Deploy

pyinfra is desigend around the idea of defining the end-state _before_ excuting any changes on the remote server. Generally this works well but sometimes you need the output of one command to feed into another. This can be achieved by executing Python functions mid-deploy.

In this example we install a service (ZeroTier) that generates a random ID for the remote host. We then use this ID to authenticate the server with the ZeroTier API.

```py
import requests

from pyinfra.modules import apt, python, server


# Assumes the repo is configured/apt is updated
apt.packages(
    {'Install ZeroTier'},
    'zerotier-one',
)


def authorize_server(state, host):
    # Run a command on the server and collect status, stderr and stdout
    status, stdout, stderr = host.run_shell_command('cat /var/lib/zerotier-one/identity.public')
    assert status == 0  # ensure the command executed OK

    # First line of output is the identity
    server_id = stdout[0]

    # Authorize via the ZeroTier API
    response = requests.post('https://my.zerotier.com/.../{0}'.format(server_id))
    response.raise_for_status()


python.call(
    {'Authorize the server on ZeroTier'},
    authorize_server,
)

server.shell(
    {'Execute some shell'},
    'echo "back to other operations!"',
)
```
