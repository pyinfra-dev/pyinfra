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
    deploy_dir = '/'
    in_op = True
    pipelining = False

    def __init__(self):
        self.inventory = Inventory(([], {}))
        self.config = Config()

    def get_temp_filename(*args):
        return '_tempfile_'


def parse_fact(fact):
    '''
    Convert JSON types to more complex Python types because JSON is lacking.
    '''

    # Handle datetimes
    if isinstance(fact, six.string_types) and fact.startswith('datetime:'):
        return datetime.strptime(fact[9:], '%Y-%m-%dT%H:%M:%S')

    elif isinstance(fact, list):
        # Handle sets
        if len(fact) > 1 and fact[0] == '_set':
            return set(parse_fact(value) for value in fact[1:])

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

    def __iter__(self):
        return iter(self.data)

    def __getattr__(self, key):
        return getattr(self.data, key)

    def __getitem__(self, key):
        return self.data[key]

    def __contains__(self, key):
        return key in self.data

    def __call__(self, *args, **kwargs):
        item = self.data

        for arg in args:
            if arg is None:
                continue

            item = item[arg]

        return item

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


class FakeFile(object):
    _read = False
    _data = None

    def __init__(self, name, data=None):
        self._name = name
        self._data = data

    def read(self, *args, **kwargs):
        if self._read is False:
            self._read = True

            if self._data:
                return self._data
            else:
                return '_test_data_'

        return ''

    def readlines(self, *args, **kwargs):
        if self._read is False:
            self._read = True

            if self._data:
                return self._data.split()
            else:
                return ['_test_data_']

            return []

    def seek(self, *args, **kwargs):
        pass

    def close(self, *args, **kwargs):
        pass

    def __enter__(self, *args, **kwargs):
        return self

    def __exit__(self, *args, **kwargs):
        pass


class patch_files(object):
    def __init__(self, patch_files):
        files = []
        files_data = {}

        for filename_data in patch_files:
            if isinstance(filename_data, list):
                filename, data = filename_data
            else:
                filename = filename_data
                data = None

            filename = '{0}{1}'.format(FakeState.deploy_dir, filename)
            files.append(filename)

            if data:
                files_data[filename] = data

        self.files = files
        self.files_data = files_data

    def __enter__(self):
        self.patches = [
            patch(
                'pyinfra.modules.files.path.isfile',
                lambda *args, **kwargs: True, create=True
            ),
            patch('pyinfra.modules.files.open', self.get_file, create=True),
            patch('pyinfra.api.util.open', self.get_file, create=True),
        ]

        for patched in self.patches:
            patched.start()

    def __exit__(self, type_, value, traceback):
        for patched in self.patches:
            patched.stop()

    def get_file(self, filename, *args):
        if filename in self.files:
            return FakeFile(filename, self.files_data.get(filename))

        raise IOError('Missing FakeFile: {0}'.format(filename))


def create_host(name=None, facts=None, data=None):
    '''
    Creates a FakeHost object with attached fact data.
    '''

    real_facts = {}
    facts = facts or {}

    for name, fact_data in six.iteritems(facts):
            real_facts[name] = fact_data

    return FakeHost(name, facts=real_facts, data=data)
