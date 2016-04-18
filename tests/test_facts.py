# pyinfra
# File: tests/test_facts.py
# Desc: generate tests for facts

from __future__ import print_function

import json
from os import path, listdir
from unittest import TestCase

import six
from nose.tools import nottest
from jsontest import JsonTest

from pyinfra.cli import json_encode
from pyinfra.api.facts import FACTS


@nottest
def make_fact_tests(fact_name):
    fact = FACTS[fact_name]()

    @six.add_metaclass(JsonTest)
    class TestTests(TestCase):
        jsontest_files = path.join('tests', 'facts', fact_name)

        def jsontest_function(self, test_name, test_data):
            if 'arg' in test_data:
                fact.command(test_data['arg'])

            data = fact.process(test_data['output'])

            # Encode/decode data to ensure datetimes/etc become JSON
            data = json.loads(json.dumps(data, default=json_encode))
            try:
                self.assertEqual(data, test_data['fact'])
            except AssertionError as e:
                print()
                print('--> GOT:\n', json.dumps(data, indent=4, default=json_encode))
                print('--> WANT:', json.dumps(
                    test_data['fact'], indent=4, default=json_encode
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
