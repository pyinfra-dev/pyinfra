from __future__ import print_function

import json

from os import listdir, path
from unittest import TestCase

import six
from jsontest import JsonTest
from nose.tools import nottest

from pyinfra.api.facts import FACTS, ShortFactBase
from pyinfra_cli.util import json_encode


@nottest
def make_fact_tests(fact_name):
    fact = FACTS[fact_name]()

    @six.add_metaclass(JsonTest)
    class TestTests(TestCase):
        jsontest_files = path.join('tests', 'facts', fact_name)
        jsontest_prefix = 'test_{0}_'.format(fact_name)

        def jsontest_function(self, test_name, test_data, fact=fact):
            short_fact = None

            if isinstance(fact, ShortFactBase):
                short_fact = fact
                fact = fact.fact()

            if callable(fact.command):
                args = test_data.get('arg', [])
                if not isinstance(args, list):
                    args = [args]

                command = fact.command(*args)

                if args or 'command' in test_data:
                    self.assertEqual(command, test_data['command'])

            elif 'command' in test_data:
                self.assertEqual(fact.command, test_data['command'])

            data = fact.process(test_data['output'])
            if short_fact:
                data = short_fact.process_data(data)

            # Encode/decode data to ensure datetimes/etc become JSON
            data = json.loads(json.dumps(data, default=json_encode))
            try:
                self.assertEqual(data, test_data['fact'])
            except AssertionError as e:
                print()
                print('--> GOT:\n', json.dumps(data, indent=4, default=json_encode))
                print('--> WANT:', json.dumps(
                    test_data['fact'], indent=4, default=json_encode,
                ))
                raise e

    TestTests.__name__ = 'Fact{0}'.format(fact_name)
    return TestTests


# Find available fact tests
fact_tests = [
    filename
    for filename in listdir(path.join('tests', 'facts'))
    if path.isdir(path.join('tests', 'facts', filename))
]

# Generate the classes, attaching to local
for fact_name in fact_tests:
    locals()[fact_name] = make_fact_tests(fact_name)
