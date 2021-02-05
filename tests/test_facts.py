from __future__ import print_function

import json
import warnings

from importlib import import_module
from os import listdir, path
from unittest import TestCase

import six

from pyinfra.api import StringCommand
from pyinfra.api.facts import FACTS, ShortFactBase
from pyinfra_cli.util import json_encode

from .util import get_command_string, JsonTest

# show full diff on json
TestCase.maxDiff = None


def _make_command(command_attribute, args):
    if callable(command_attribute):
        if not isinstance(args, list):
            args = [args]

        return command_attribute(*args)
    return command_attribute


def make_fact_tests(folder_name):
    if '.' in folder_name:
        module_name, fact_name = folder_name.split('.')
        module = import_module('pyinfra.facts.{0}'.format(module_name))
        fact = getattr(module, fact_name)()
    else:
        fact = FACTS[folder_name]()

    @six.add_metaclass(JsonTest)
    class TestTests(TestCase):
        jsontest_files = path.join('tests', 'facts', folder_name)
        jsontest_prefix = 'test_{0}_'.format(fact.name)

        def jsontest_function(self, test_name, test_data, fact=fact):
            short_fact = None

            if isinstance(fact, ShortFactBase):
                short_fact = fact
                fact = fact.fact()

            test_args = test_data.get('arg', [])
            command = _make_command(fact.command, test_args)

            if 'command' in test_data:
                assert get_command_string(StringCommand(command)) == test_data['command']
            else:
                warnings.warn('No command set for test: {0} (got "{1}")'.format(
                    test_name, command,
                ))

            requires_command = _make_command(fact.requires_command, test_args)

            if requires_command:
                if 'requires_command' in test_data:
                    assert requires_command == test_data['requires_command']
                else:
                    warnings.warn('No requires command set for test: {0} (got "{1}")'.format(
                        test_name, requires_command,
                    ))

            data = fact.process(test_data['output'])
            if short_fact:
                data = short_fact.process_data(data)

            # Encode/decode data to ensure datetimes/etc become JSON
            data = json.loads(json.dumps(data, default=json_encode))
            try:
                assert data == test_data['fact']
            except AssertionError as e:
                print()
                print('--> GOT:\n', json.dumps(data, indent=4, default=json_encode))
                print('--> WANT:', json.dumps(
                    test_data['fact'], indent=4, default=json_encode,
                ))
                raise e

    TestTests.__name__ = 'Fact{0}'.format(fact.name)
    return TestTests


# Find available fact tests
fact_tests = sorted([
    filename
    for filename in listdir(path.join('tests', 'facts'))
    if path.isdir(path.join('tests', 'facts', filename))
])

# Generate the classes, attaching to local
for fact_name in fact_tests:
    locals()[fact_name] = make_fact_tests(fact_name)
