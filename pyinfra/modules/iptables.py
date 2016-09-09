# pyinfra
# File: pyinfra/modules/iptables.py
# Desc: manage iptables rules

'''
The iptables modules handles iptables rules
'''

from __future__ import unicode_literals

from pyinfra.api import operation


@operation
def forward(state, host, dport, to_ip, to_port=None,
            interface='eth0', protocol='tcp'):
    '''
    Manage an iptables rule to forward packets arriving on a given port and
    interface to another host.

    + dport: port on which the packets are arriving
    + to_ip: ip of the destination
    + to_port: port of the destination (default to dport)
    + interface: interface on which the packets are arriving
    + protocol: protocol (tcp or udp)

    '''
    to_port = to_port or dport
    definition = {
        'dport': dport,
        'destination': '{}:{}'.format(to_ip, to_port),
        'interface': interface,
        'protocol': protocol,
    }
    commands = [
        ('iptables -t nat -A PREROUTING '
         '-i {interface} -p {protocol} -m {protocol} '
         '--dport {dport} -j DNAT --to-destination {destination}'
         ).format(**definition)
    ]
    return commands
