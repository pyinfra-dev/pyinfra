# pyinfra
# File: tests/test_modules.py
# Desc: generate tests for module operations

from os import listdir, path
from unittest import TestCase
from importlib import import_module

from nose.tools import nottest
from jsontest import JsonTest

from .util import FakeState, create_host


@nottest
def make_operation_tests(arg):
    # Get the operation we're testing against
    module_name, op_name = arg.split('.')
    module = import_module('pyinfra.modules.{0}'.format(module_name))
    op = getattr(module, op_name)

    # Generate a test class
    class TestTests(TestCase):
        __metaclass__ = JsonTest

        jsontest_files = path.join('tests', 'operations', arg)

        @classmethod
        def setUpClass(cls):
            cls.state = FakeState()

        def jsontest_function(self, test_name, test_data):
            host = create_host(test_data['facts'])

            commands = op._pyinfra_op(
                self.state, host,
                *test_data['args'], **test_data['kwargs']
            )

            print
            print commands
            print test_data['commands']

            self.assertEqual(commands, test_data['commands'])

    # Convert the op name (module.op) to a class name ModuleOp
    test_name = (
        arg.replace('.', ' ')
        .title()
        .replace(' ', '')
    )

    # Set the name
    TestTests.__name__ = 'TestOperation{0}'.format(test_name)
    return TestTests


# Find available operation tests
operations = [
    filename
    for filename in listdir(path.join('tests', 'operations'))
    if path.isdir(path.join('tests', 'operations', filename))
]

# Generate the classes, attaching to locals so nose picks them up
for operation_name in operations:
    locals()[operation_name] = make_operation_tests(operation_name)
