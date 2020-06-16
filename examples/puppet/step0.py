from pyinfra import host
from pyinfra.modules import server

SUDO = True

ip = host.fact.ipv4_addresses['eth0']

if ip.startswith('10.'):
    server.script(
        {'Remove 10. network from eth0'},
        'files/remove_10_on_eth0.bash',
    )
