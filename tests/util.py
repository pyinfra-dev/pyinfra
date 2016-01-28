# pyinfra
# File: tests/util.py
# Desc: utilities for fake pyinfra state/host objects

from pyinfra.api import Config


class FakeState(object):
    active = True
    deploy_dir = ''
    in_op = True

    config = Config()


class FakeFact(object):
    def __init__(self, data):
        self.data = data

    def __getattr__(self, key):
        return self.data[key]

    def __call__(self, arg):
        return self.data[arg]

    def __iter__(self):
        return iter(self.data)

    def get(self, key, default=None):
        if key in self.data:
            return self.data[key]

        return default


class FakeHost(object):
    def __init__(self, facts):
        self.facts = facts

    def __getattr__(self, key):
        if self.facts[key] is None:
            return None
        else:
            return FakeFact(self.facts[key])


def create_host(fact_data):
    '''Creates a FakeHost object with attached fact data.'''

    facts = {}

    for name, data in fact_data.iteritems():
        if ':' in name:
            name, arg = name.split(':')
            facts.setdefault(name, {})[arg] = data
        else:
            facts[name] = data

    return FakeHost(facts)
