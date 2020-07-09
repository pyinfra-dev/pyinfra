from pyinfra import host
from pyinfra.operations import server

SUDO = True

ip = host.fact.ipv4_addresses['eth0']

if ip.startswith('10.'):
    server.script(
        name='Remove 10. network from eth0',
        src='files/remove_10_on_eth0.bash',
    )
