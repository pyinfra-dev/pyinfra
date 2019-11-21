from __future__ import print_function

import json
from importlib import import_module
from os import listdir, path
from types import FunctionType
from unittest import TestCase

import six
from jsontest import JsonTest
from nose.tools import nottest

from pyinfra import pseudo_host, pseudo_state
from pyinfra.api.util import unroll_generators
from pyinfra_cli.util import json_encode

from .util import create_host, FakeState, patch_files


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
        jsontest_prefix = 'test_{0}_{1}_'.format(module_name, op_name)

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

            with patch_files(test_data.get('files', []), test_data.get('directories', [])):
                try:
                    output_commands = unroll_generators(op._pyinfra_op(
                        pseudo_state, pseudo_host,
                        *test_data.get('args', []), **test_data.get('kwargs', {})
                    )) or []
                except Exception as e:
                    if allowed_exception:
                        allowed_exception_names = allowed_exception.get('names')
                        if not allowed_exception_names:
                            allowed_exception_names = [allowed_exception['name']]

                        if e.__class__.__name__ not in allowed_exception_names:
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
                    if command[0] == '__func__':
                        commands.append([
                            command[0], list(command[1]), command[2],
                        ])
                    elif isinstance(command[0], FunctionType):
                        commands.append([
                            command[0].__name__, list(command[1]), command[2],
                        ])
                    else:
                        if hasattr(command[1], 'read'):
                            command[1].seek(0)
                            data = command[1].read()
                        else:
                            data = command[1]

                        commands.append([command[0], data, command[2]])

                else:
                    commands.append(command)

            try:
                self.assertEqual(commands, test_data['commands'])
            except AssertionError as e:
                print()
                print('--> COMMANDS OUTPUT:')
                print(json.dumps(commands, indent=4, default=json_encode))

                print('--> TEST WANTS:')
                print(json.dumps(
                    test_data['commands'], indent=4, default=json_encode,
                ))

                raise e

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
