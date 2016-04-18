# pyinfra
# File: tests/util.py
# Desc: utilities for fake pyinfra state/host objects

from datetime import datetime

import six
from mock import patch

from pyinfra.api import Config, Inventory
from pyinfra.api.attrs import AttrData


class FakeState(object):
    active = True
    deploy_dir = ''
    in_op = True
    pipelining = False

    def __init__(self):
        self.inventory = Inventory(([], {}))
        self.config = Config()

    def get_temp_filename(*args):
        return '_tempfile_'


def parse_fact(fact):
    if isinstance(fact, six.string_types) and fact.startswith('datetime:'):
        return datetime.strptime(fact[9:], '%Y-%m-%dT%H:%M:%S')

    elif isinstance(fact, list):
        return [parse_fact(value) for value in fact]

    elif isinstance(fact, dict):
        return {
            key: parse_fact(value)
            for key, value in six.iteritems(fact)
        }

    return fact


class FakeFact(object):
    def __init__(self, data):
        self.data = parse_fact(data)

    def __getattr__(self, key):
        return getattr(self.data, key)

    def __getitem__(self, key):
        return self.data[key]

    def __call__(self, *args, **kwargs):
        return self.data[args[0]]

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


class FakeFile(file):
    _read = False

    def __init__(self, name):
        self._name = name

    def read(self, *args, **kwargs):
        if self._read is False:
            self._read = True
            return '_test_data_'

        return ''

    def seek(self, *args, **kwargs):
        pass


class PatchFiles(object):
    def __init__(self, files):
        self.files = files

    def __enter__(self):
        self.patched = patch('pyinfra.api.util.open', self.get_file, create=True)
        self.patched.start()

    def __exit__(self, type_, value, traceback):
        self.patched.stop()

    def get_file(self, filename, *args):
        if filename in self.files:
            return FakeFile(filename)


def patch_files(files=None):
    return PatchFiles(files)


def create_host(name=None, facts=None, data=None):
    '''
    Creates a FakeHost object with attached fact data.
    '''

    real_facts = {}
    facts = facts or {}

    for name, fact_data in six.iteritems(facts):
        if ':' in name:
            args = name.split(':')
            name = args[0]
            args = args[1]
            real_facts.setdefault(name, {})[args] = fact_data
        else:
            real_facts[name] = fact_data

    return FakeHost(name, facts=real_facts, data=data)
