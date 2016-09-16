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
            interface='eth0', protocol='tcp', chain='PREROUTING', jump='DNAT',
            present=True):
    '''
    Manage an iptables rule to forward packets arriving on a given port and
    interface to another host.

    + dport: port on which the packets are arriving
    + to_ip: ip of the destination
    + to_port: port of the destination (default to dport)
    + interface: interface on which the packets are arriving
    + protocol: protocol (tcp or udp)
    + chain: iptables chain (PREROUTING, POSTROUTING, OUTPUT)
    + jump: target of the rule (eg: DNAT)
    + present: whether the rule should be present or removed
    '''
    to_port = to_port or dport
    definition = {
        'dport': str(dport),
        'destination': '{}:{}'.format(to_ip, to_port),
        'interface': interface,
        'protocol': protocol,
        'match': protocol,
        'chain': chain,
        'jump': jump,
    }

    if definition in host.fact.iptables('nat'):
        if present:
            # Not removing the rule if it should be present:
            return []
        else:
            # Command to remove the rule, note -D instead of -A:
            return [(
                'iptables -t nat -D {chain} '
                '-i {interface} -p {protocol} -m {protocol} '
                '--dport {dport} -j {jump} --to-destination {destination}'
                ).format(**definition)
            ]

    else:
        if not present:
            # Not adding the rule if it should be absent:
            return []
        else:
            # Command to add the rule:
            return [(
                'iptables -t nat -A {chain} '
                '-i {interface} -p {protocol} -m {protocol} '
                '--dport {dport} -j DNAT --to-destination {destination}'
                ).format(**definition)
            ]
