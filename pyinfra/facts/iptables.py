# pyinfra
# File: pyinfra/facts/iptables.py
# Desc: facts for the Linux iptables firewall

from __future__ import unicode_literals
from collections import OrderedDict

from pyinfra.api import FactBase

IPTABLES_ARGS = {
    '--dport': 'dport',
    '-p': 'protocol',
    '--to-destination': 'destination',
    '-i': 'interface',
}


def parse_rule(line):
    "Parse one iptables rule"
    line = line.split()
    keys = line[::2]
    values = line[1::2]
    # tuples with raw iptable argument names
    raw_definition = zip(keys, values)
    # dict with keys mapped to readable names when known
    return {
        IPTABLES_ARGS.get(key, key): value
        for key, value in raw_definition
    }


def parse_rules(output):
    "Parse iptables rules from an output list"
    for line in output:
        if line.startswith('-'):
            yield parse_rule(line)


class Iptables(FactBase):
    '''
    Sorted and parsed list of iptables rules from a specific table
    '''
    def command(self, name='nat'):
        return 'iptables-save -t {0}'.format(name)

    def process(self, output):
        return list(parse_rules(output))


class IptablesForward(Iptables):
    '''
    Check if a specific iptables port forwarding rule is present
    '''

    def command(self, dport, to_ip, to_port=None,
                interface='eth0', protocol='tcp'):
        to_port = to_port or dport
        self.definition = {
            'dport': str(dport),
            'destination': '{}:{}'.format(to_ip, to_port),
            'interface': interface,
            'protocol': protocol,
        }
        return 'iptables-save -t nat'

    def process(self, output):
        'List of matching rules'
        # Using a set to match subset dictionnaries
        result = []
        looking_for = set(self.definition.items())
        for rule in parse_rules(output):
            if looking_for.issubset(set(rule.items())):
                result.append(rule)
        return result
