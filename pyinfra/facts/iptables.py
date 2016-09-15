# pyinfra
# File: pyinfra/facts/iptables.py
# Desc: facts for the Linux iptables firewall

from __future__ import unicode_literals

from pyinfra.api import FactBase

# Mapping for iptables code arguments to variable names that can be manipulated
# from Python
IPTABLES_ARGS = {
    '--dport': 'dport',
    '-p': 'protocol',
    '--to-destination': 'destination',
    '-i': 'interface',
    '-A': 'chain',
    '-m': 'match',
    '-j': 'jump',
}


def parse_rule(line):
    '''
    Parse one iptables rule. Returns a dict where each iptables code argument
    is mapped to a name using IPTABLES_ARGS.

    + line: line matching a rule
    '''
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
    "Parse iptables rules from an iptables-save output list"
    for line in output:
        # Rules start with '-'
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
