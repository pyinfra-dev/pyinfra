import json
import os
from datetime import datetime
from inspect import getfullargspec
from io import open
from os import listdir, path
from pathlib import Path
from unittest.mock import patch

from pyinfra.api import Config, Inventory
from pyinfra.api.util import get_kwargs_str

from . import logger


def get_command_string(command):
    value = command.get_raw_value()
    masked_value = command.get_masked_value()
    if value == masked_value:
        return value
    return [value, masked_value]


def make_inventory(hosts=("somehost", "anotherhost"), **kwargs):
    override_data = kwargs.pop("override_data", {})
    if "ssh_user" not in override_data:
        override_data["ssh_user"] = "vagrant"

    return Inventory(
        (hosts, {}),
        override_data=override_data,
        test_group=(
            [
                "somehost",
            ],
            {
                "group_data": "hello world",
            },
        ),
        **kwargs,
    )


class FakeState:
    active = True
    cwd = "/"
    in_op = True
    in_deploy = True
    pipelining = False
    is_executing = False
    deploy_name = None
    deploy_kwargs = None

    def __init__(self):
        self.inventory = Inventory(([], {}))
        self.config = Config()

    def get_temp_filename(*args):
        return "_tempfile_"


def parse_value(value):
    """
    Convert JSON types to more complex Python types because JSON is lacking.
    """

    if isinstance(value, str):
        if value.startswith("datetime:"):
            return datetime.strptime(value[9:], "%Y-%m-%dT%H:%M:%S")
        if value.startswith("path:"):
            return Path(value[5:])
        return value

    if isinstance(value, list):
        if value and value[0] == "set:":
            return set(parse_value(value) for value in value[1:])
        return [parse_value(value) for value in value]

    if isinstance(value, dict):
        return {key: parse_value(value) for key, value in value.items()}

    return value


class FakeFact:
    def __init__(self, data):
        self.data = parse_value(data)

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


class FakeFacts:
    def __init__(self, facts):
        self.facts = {key: FakeFact(value) for key, value in facts.items()}

    def __getattr__(self, key):
        return self.facts.get(key)

    def __setitem__(self, key, value):
        self.facts[key] = value

    def _create(self, key, data=None, args=None):
        self.facts[key][args[0]] = data

    def _delete(self, key, args=None):
        self.facts[key].pop(args[0], None)


# TODO: remove after python2 removal, as only required because of different default ordering in 2/3
def _sort_kwargs_str(string):
    return ", ".join(sorted(string.split(", ")))


class FakeHost:
    noop_description = None

    # Current context inside an @operation function
    in_op = True
    current_op_hash = None
    current_op_global_kwargs = None

    # Current context inside a @deploy function
    in_deploy = True
    current_deploy_name = None
    current_deploy_kwargs = None
    current_deploy_data = None

    def __init__(self, name, facts, data):
        self.name = name
        self.fact = FakeFacts(facts)
        self.data = data
        self.connector_data = {}

    @property
    def print_prefix(self):
        return ""

    def noop(self, description):
        self.noop_description = description

    @staticmethod
    def _get_fact_key(fact_cls):
        return "{0}.{1}".format(fact_cls.__module__.split(".")[-1], fact_cls.__name__)

    @staticmethod
    def _check_fact_args(fact_cls, kwargs):
        # Check that the arguments we're going to use to fake a fact are all actual arguments in
        # the fact class, otherwise the test will hide a bug in the underlying operation.
        real_args = getfullargspec(fact_cls.command)
        for key in kwargs.keys():
            assert (
                key in real_args.args
            ), f"Argument {key} is not a real argument in the `{fact_cls}.command` method"

    def get_fact(self, fact_cls, **kwargs):
        fact_key = self._get_fact_key(fact_cls)
        fact = getattr(self.fact, fact_key, None)
        if fact is None:
            raise KeyError("Missing test fact data: {0}".format(fact_key))
        if kwargs:
            self._check_fact_args(fact_cls, kwargs)
            fact_ordered_keys = {_sort_kwargs_str(key): value for key, value in fact.items()}
            kwargs_str = _sort_kwargs_str(get_kwargs_str(kwargs))
            if kwargs_str not in fact:
                logger.info("Possible missing fact key: {0}".format(kwargs_str))
            return fact_ordered_keys.get(kwargs_str)
        return fact

    def create_fact(self, fact_cls, data=None, kwargs=None):
        try:
            fact = self.get_fact(fact_cls)
        except KeyError:
            fact_key = self._get_fact_key(fact_cls)
            fact = self.fact[fact_key] = {}
        if kwargs:
            fact[_sort_kwargs_str(get_kwargs_str(kwargs))] = data
        else:
            fact_key = self._get_fact_key(fact_cls)
            self.fact[fact_key] = data

    def delete_fact(self, fact_cls, kwargs=None):
        try:
            fact = self.get_fact(fact_cls)
        except KeyError:
            return

        ordered_kwargs = _sort_kwargs_str(get_kwargs_str(kwargs))
        for key in fact.keys():
            ordered_key = _sort_kwargs_str(key)
            if ordered_key == ordered_kwargs:
                fact.pop(key)
                break


class FakeFile:
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
            return "_test_data_"

        return ""

    def readlines(self, *args, **kwargs):
        if self._read is False:
            self._read = True

            if self._data:
                return self._data.split()
            return ["_test_data_"]

            return []

    def seek(self, *args, **kwargs):
        pass

    def close(self, *args, **kwargs):
        pass

    def __enter__(self, *args, **kwargs):
        return self

    def __exit__(self, *args, **kwargs):
        pass


class patch_files:
    def __init__(self, local_files):
        directories, files, files_data = self._parse_local_files(local_files)

        self._files = files
        self._files_data = files_data
        self._directories = directories

    @staticmethod
    def _parse_local_files(local_files, prefix=FakeState.cwd):
        files = []
        files_data = {}
        directories = {}

        prefix = path.normpath(prefix)

        for filename, file_data in local_files.get("files", {}).items():
            filepath = path.join(prefix, filename)
            files.append(filepath)
            files_data[filepath] = file_data

        for dirname, dir_files in local_files.get("dirs", {}).items():
            sub_dirname = path.join(prefix, dirname)
            sub_directories, sub_files, sub_files_data = patch_files._parse_local_files(
                dir_files,
                sub_dirname,
            )

            files.extend(sub_files)
            files_data.update(sub_files_data)

            directories[sub_dirname] = {
                "files": list(dir_files["files"].keys()),
                "dirs": list(dir_files["dirs"].keys()),
            }
            directories.update(sub_directories)

        return directories, files, files_data

    def __enter__(self):
        self.patches = [
            patch("pyinfra.operations.files.os.path.exists", self.exists),
            patch("pyinfra.operations.files.os.path.isfile", self.isfile),
            patch("pyinfra.operations.files.os.path.isdir", self.isdir),
            patch("pyinfra.operations.files.os.walk", self.walk),
            patch("pyinfra.operations.files.os.makedirs", lambda path: True),
            patch("pyinfra.api.util.stat", self.stat),
            # Builtin patches
            patch("pyinfra.operations.files.open", self.get_file, create=True),
            patch("pyinfra.operations.server.open", self.get_file, create=True),
            patch("pyinfra.api.util.open", self.get_file, create=True),
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

        raise IOError("Missing FakeFile: {0}".format(filename))

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
            raise IOError("No such file or directory: {0}".format(pathname))

        return os.stat_result((mode_int, 0, 0, 0, 0, 0, 0, 0, 0, 0))

    def walk(self, dirname, topdown=True, onerror=None, followlinks=False):
        if not self.isdir(dirname):
            return

        normalized_path = path.normpath(dirname)
        dir_definition = self._directories[normalized_path]
        child_dirs = dir_definition.get("dirs", [])
        child_files = dir_definition.get("files", [])

        yield dirname, child_dirs, child_files

        for child in child_dirs:
            full_child = path.join(dirname, child)
            for recursive_return in self.walk(full_child, topdown, onerror, followlinks):
                yield recursive_return


def create_host(name=None, facts=None, data=None):
    """
    Creates a FakeHost object with attached fact data.
    """

    real_facts = {}
    facts = facts or {}
    data = data or {}

    for name, fact_data in facts.items():
        real_facts[name] = fact_data

    return FakeHost(name, facts=real_facts, data=data)


class JsonTest(type):
    def __new__(cls, name, bases, attrs):
        # Get the JSON files
        files = listdir(attrs["jsontest_files"])
        files = [f for f in files if f.endswith(".json")]

        test_prefix = attrs.get("jsontest_prefix", "test_")

        def gen_test(test_name, filename):
            def test(self):
                test_data = json.loads(
                    open(
                        path.join(attrs["jsontest_files"], filename),
                        encoding="utf-8",
                    ).read(),
                )
                self.jsontest_function(test_name, test_data)

            return test

        # Loop them and create class methods to call the jsontest_function
        for filename in files:
            test_name = filename[:-5]

            # Attach the method
            method_name = "{0}{1}".format(test_prefix, test_name)
            attrs[method_name] = gen_test(test_name, filename)

        return type.__new__(cls, name, bases, attrs)
