# pyinfra
# File: tests/test_modules.py
# Desc: generate tests for module operations

from __future__ import print_function

import json
from os import listdir, path
from unittest import TestCase
from importlib import import_module
from types import FunctionType

import six
from nose.tools import nottest
from jsontest import JsonTest

from pyinfra import pseudo_state, pseudo_host
from pyinfra.cli import json_encode
from pyinfra.api.util import unroll_generators

from .util import FakeState, create_host, patch_files


@nottest
def make_operation_tests(arg):
    # Get the operation we're testing against
    module_name, op_name = arg.split('.')
    module = import_module('pyinfra.modules.{0}'.format(module_name))
    op = getattr(module, op_name)

    # Generate a test class
    @six.add_metaclass(JsonTest)
    class TestTests(TestCase):
        jsontest_files = path.join('tests', 'operations', arg)

        @classmethod
        def setUpClass(cls):
            # Create a global fake state that attach to pseudo state
            cls.state = FakeState()
            pseudo_state.set(cls.state)

        def jsontest_function(self, test_name, test_data):
            # Create a host with this tests facts and attach to pseudo host
            host = create_host(facts=test_data.get('facts', {}))
            pseudo_host.set(host)

            allowed_exception = test_data.get('exception')

            with patch_files(test_data.get('files', [])):
                try:
                    output_commands = unroll_generators(op._pyinfra_op(
                        pseudo_state, pseudo_host,
                        *test_data.get('args', []), **test_data.get('kwargs', {})
                    )) or []
                except Exception as e:
                    if allowed_exception:
                        if e.__class__.__name__ != allowed_exception['name']:
                            print('Wrong execption raised!')
                            raise

                        self.assertEqual(e.args[0], allowed_exception['message'])
                        return

                    raise

            commands = []

            for command in output_commands:
                if isinstance(command, six.string_types):
                    commands.append(command.strip())

                elif isinstance(command, dict):
                    command['command'] = command['command'].strip()
                    commands.append(command)

                elif isinstance(command, tuple):
                    if isinstance(command[0], FunctionType):
                        commands.append(command)
                    else:
                        if hasattr(command[0], 'read'):
                            data = command[0].read()
                        else:
                            data = command[0]

                        commands.append([data, command[1]])

                else:
                    commands.append(command)

            try:
                self.assertEqual(commands, test_data['commands'])
            except AssertionError as e:
                print()
                print('--> GOT:\n', json.dumps(commands, indent=4, default=json_encode))
                print('--> WANT:', json.dumps(
                    test_data['commands'], indent=4, default=json_encode
                ))
                raise e

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
