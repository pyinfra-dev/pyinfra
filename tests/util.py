# pyinfra
# File: tests/util.py
# Desc: utilities for fake pyinfra state/host objects

from pyinfra.api import Config
from pyinfra.api.attrs import AttrData


class FakeState(object):
    active = True
    deploy_dir = ''
    in_op = True
    pipelining = False

    config = Config()

    def get_temp_filename(*args):
        return '_tempfile_'


class FakeFact(object):
    def __init__(self, data):
        self.data = data

    def __getattr__(self, key):
        return self.data[key]

    def __getitem__(self, key):
        return self.data[key]

    def __call__(self, arg):
        return self.data[arg]

    def __iter__(self):
        return iter(self.data)

    def get(self, key, default=None):
        if key in self.data:
            return self.data[key]

        return default


class FakeFacts(object):
    def __init__(self, facts):
        self.facts = facts

    def __getattr__(self, key):
        if self.facts[key] is None:
            return None
        else:
            return FakeFact(self.facts[key])


class FakeHost(object):
    def __init__(self, name, facts, data):
        self.name = name
        self.fact = FakeFacts(facts)
        self.data = AttrData(data)


def create_host(name=None, facts=None, data=None):
    '''
    Creates a FakeHost object with attached fact data.
    '''

    real_facts = {}
    facts = facts or {}

    for name, fact_data in facts.iteritems():
        if ':' in name:
            name, arg = name.split(':')
            real_facts.setdefault(name, {})[arg] = fact_data
        else:
            real_facts[name] = fact_data

    return FakeHost(name, facts=real_facts, data=data)
