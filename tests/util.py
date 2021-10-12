import json
import os

from datetime import datetime
from io import open
from os import listdir, path

import six
from mock import patch

from pyinfra.api import Config, Inventory
from pyinfra.api.util import get_kwargs_str

from . import logger


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
        self.connector_data = {}

    @property
    def print_prefix(self):
        return ''

    def noop(self, description):
        self.noop_description = description

    def get_fact(self, fact_cls, **kwargs):
        fact_key = '{0}.{1}'.format(fact_cls.__module__.split('.')[-1], fact_cls.__name__)
        fact = getattr(self.fact, fact_key, None)
        if fact is None:
            raise KeyError('Missing test fact data: {0}'.format(fact_key))
        if kwargs:
            kwargs_str = get_kwargs_str(kwargs)
            if kwargs_str not in fact:
                logger.info('Possible missing fact key: {0}'.format(kwargs_str))
            return fact.get(kwargs_str)
        return fact

    def create_fact(self, fact_cls, data, kwargs):
        fact = self.get_fact(fact_cls)
        fact[get_kwargs_str(kwargs)] = data

    def delete_fact(self, fact_cls, kwargs):
        fact = self.get_fact(fact_cls)
        fact.pop(get_kwargs_str(kwargs), None)


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
    def __init__(self, local_files):
        directories, files, files_data = self._parse_local_files(local_files)

        self._files = files
        self._files_data = files_data
        self._directories = directories

    @staticmethod
    def _parse_local_files(local_files, prefix=FakeState.deploy_dir):
        files = []
        files_data = {}
        directories = {}

        prefix = path.normpath(prefix)

        for filename, file_data in local_files.get('files', {}).items():
            filepath = path.join(prefix, filename)
            files.append(filepath)
            files_data[filepath] = file_data

        for dirname, dir_files in local_files.get('dirs', {}).items():
            sub_dirname = path.join(prefix, dirname)
            sub_directories, sub_files, sub_files_data = patch_files._parse_local_files(
                dir_files,
                sub_dirname,
            )

            files.extend(sub_files)
            files_data.update(sub_files_data)

            directories[sub_dirname] = {
                'files': list(dir_files['files'].keys()),
                'dirs': list(dir_files['dirs'].keys()),
            }
            directories.update(sub_directories)

        return directories, files, files_data

    def __enter__(self):
        self.patches = [
            patch('pyinfra.operations.files.os_path.exists', self.exists),
            patch('pyinfra.operations.files.os_path.isfile', self.isfile),
            patch('pyinfra.operations.files.os_path.isdir', self.isdir),
            patch('pyinfra.operations.files.walk', self.walk),
            patch('pyinfra.operations.files.makedirs', lambda path: True),
            patch('pyinfra.api.util.stat', self.stat),
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
        if self.isfile(filename):
            normalized_path = path.normpath(filename)
            return FakeFile(normalized_path, self._files_data.get(normalized_path))

        raise IOError('Missing FakeFile: {0}'.format(filename))

    def exists(self, filename, *args):
        return self.isfile(filename) or self.isdir(filename)

    def isfile(self, filename, *args):
        normalized_path = path.normpath(filename)
        return normalized_path in self._files

    def isdir(self, dirname, *args):
        normalized_path = path.normpath(dirname)
        return normalized_path in self._directories

    def stat(self, pathname):
        if self.isfile(pathname):
            mode_int = 33188  # 644 file
        elif self.isdir(pathname):
            mode_int = 16877  # 755 directory
        else:
            raise IOError('No such file or directory: {0}'.format(pathname))

        return os.stat_result((mode_int, 0, 0, 0, 0, 0, 0, 0, 0, 0))

    def walk(self, dirname, topdown=True, onerror=None, followlinks=False):
        if not self.isdir(dirname):
            return

        normalized_path = path.normpath(dirname)
        dir_definition = self._directories[normalized_path]
        child_dirs = dir_definition.get('dirs', [])
        child_files = dir_definition.get('files', [])

        yield dirname, child_dirs, child_files

        for child in child_dirs:
            full_child = path.join(dirname, child)
            for recursive_return in self.walk(full_child, topdown, onerror, followlinks):
                yield recursive_return


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
