import json
import os

from datetime import datetime
from io import open
from os import listdir, path

import six
from mock import patch

from pyinfra.api import Config, Inventory


def get_command_string(command):
    value = command.get_raw_value()
    masked_value = command.get_masked_value()
    if value == masked_value:
        return value
    else:
        return [value, masked_value]


def make_inventory(hosts=('somehost', 'anotherhost'), **kwargs):
    return Inventory(
        (hosts, {}),
        test_group=([
            'somehost',
        ], {
            'group_data': 'hello world',
        }),
        ssh_user='vagrant',
        **kwargs
    )


class FakeState(object):
    active = True
    deploy_dir = '/'
    in_op = True
    in_deploy = True
    pipelining = False
    deploy_name = None
    deploy_kwargs = None

    def __init__(self):
        self.inventory = Inventory(([], {}))
        self.config = Config()

    def get_temp_filename(*args):
        return '_tempfile_'

    def add_will_add_user(self, username):
        pass


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

    def __setitem__(self, key, value):
        self.data[key] = value

    def __contains__(self, key):
        return key in self.data

    def __call__(self, *args, **kwargs):
        item = self.data

        for arg in args:
            if arg is None:
                continue

            # Support for non-JSON-able fact arguments by  turning them into JSON!
            if isinstance(arg, list):
                arg = json.dumps(arg)

            item = item.get(arg)

        return item

    def __str__(self):
        return str(self.data)

    def __unicode__(self):
        return self.data

    def __eq__(self, other_thing):
        return self.data == other_thing

    def __ne__(self, other_thing):
        return self.data != other_thing

    def get(self, key, default=None):
        if key in self.data:
            return self.data[key]

        return default


class FakeFacts(object):
    def __init__(self, facts):
        self.facts = {
            key: FakeFact(value)
            for key, value in facts.items()
        }

    def __getattr__(self, key):
        return self.facts.get(key)

    def _create(self, key, data=None, args=None):
        self.facts[key][args[0]] = data

    def _delete(self, key, args=None):
        self.facts[key].pop(args[0], None)


class FakeHost(object):
    noop_description = None

    def __init__(self, name, facts, data):
        self.name = name
        self.fact = FakeFacts(facts)
        self.data = data

    @property
    def print_prefix(self):
        return ''

    def noop(self, description):
        self.noop_description = description


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
    def __init__(self, patch_files, patch_directories):
        files = []
        files_data = {}

        for filename_data in patch_files:
            if isinstance(filename_data, list):
                filename, data = filename_data
            else:
                filename = filename_data
                data = None

            if not filename.startswith(os.sep):
                filename = '{0}{1}'.format(FakeState.deploy_dir, filename)

            files.append(filename)

            if data:
                files_data[filename] = data

        self.files = files
        self.files_data = files_data

        self.directories = patch_directories

    def __enter__(self):
        self.patches = [
            patch('pyinfra.operations.files.os_path.exists', self.exists),
            patch('pyinfra.operations.files.os_path.isfile', self.isfile),
            patch('pyinfra.operations.files.os_path.isdir', self.isdir),
            patch('pyinfra.operations.files.walk', self.walk),
            patch('pyinfra.operations.files.makedirs', lambda path: True),
            # Builtin patches
            patch('pyinfra.operations.files.open', self.get_file, create=True),
            patch('pyinfra.operations.server.open', self.get_file, create=True),
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

    def exists(self, filename, *args):
        return filename in self.files or filename in self.directories

    def isfile(self, filename, *args):
        return filename in self.files

    def isdir(self, dirname, *args):
        return dirname in self.directories

    def walk(self, dirname):
        if dirname not in self.directories:
            return

        for dirname, filenames in sorted(self.directories[dirname].items()):
            yield dirname, None, filenames


def create_host(name=None, facts=None, data=None):
    '''
    Creates a FakeHost object with attached fact data.
    '''

    real_facts = {}
    facts = facts or {}

    for name, fact_data in six.iteritems(facts):
        real_facts[name] = fact_data

    return FakeHost(name, facts=real_facts, data=data)


class JsonTest(type):
    def __new__(cls, name, bases, attrs):
        # Get the JSON files
        files = listdir(attrs['jsontest_files'])
        files = [f for f in files if f.endswith('.json')]

        test_prefix = attrs.get('jsontest_prefix', 'test_')

        def gen_test(test_name, filename):
            def test(self):
                test_data = json.loads(open(
                    path.join(attrs['jsontest_files'], filename),
                    encoding='utf-8',
                ).read())
                self.jsontest_function(test_name, test_data)

            return test

        # Loop them and create class methods to call the jsontest_function
        for filename in files:
            test_name = filename[:-5]

            # Attach the method
            method_name = '{0}{1}'.format(test_prefix, test_name)
            attrs[method_name] = gen_test(test_name, filename)

        return type.__new__(cls, name, bases, attrs)
