from __future__ import print_function

import json
import platform
import warnings

from importlib import import_module
from os import listdir, path
from unittest import TestCase

import six
from mock import patch

from pyinfra.api import (
    FileDownloadCommand,
    FileUploadCommand,
    FunctionCommand,
    StringCommand,
)
from pyinfra.api.util import unroll_generators
from pyinfra_cli.util import json_encode

from .util import create_host, FakeState, get_command_string, JsonTest, patch_files

PLATFORM_NAME = platform.system()


def make_operation_tests(arg):
    # Get the operation we're testing against
    module_name, op_name = arg.split('.')
    module = import_module('pyinfra.operations.{0}'.format(module_name))
    op = getattr(module, op_name)

    # Generate a test class
    @patch('pyinfra.operations.files.get_timestamp', lambda: 'a-timestamp')
    @patch('pyinfra.operations.util.files.get_timestamp', lambda: 'a-timestamp')
    @six.add_metaclass(JsonTest)
    class TestTests(TestCase):
        jsontest_files = path.join('tests', 'operations', arg)
        jsontest_prefix = 'test_{0}_{1}_'.format(module_name, op_name)

        @classmethod
        def setUpClass(cls):
            # Create a global fake state that attach to pseudo state
            cls.state = FakeState()

        def jsontest_function(self, test_name, test_data):
            if (
                'require_platform' in test_data
                and PLATFORM_NAME not in test_data['require_platform']
            ):
                return

            # Create a host with this tests facts and attach to pseudo host
            host = create_host(facts=test_data.get('facts', {}))

            allowed_exception = test_data.get('exception')

            kwargs = test_data.get('kwargs', {})
            kwargs['state'] = self.state
            kwargs['host'] = host

            with patch_files(test_data.get('files', []), test_data.get('directories', [])):
                try:
                    output_commands = unroll_generators(op._pyinfra_op(
                        *test_data.get('args', []),
                        **kwargs
                    ))
                except Exception as e:
                    if allowed_exception:
                        allowed_exception_names = allowed_exception.get('names')
                        if not allowed_exception_names:
                            allowed_exception_names = [allowed_exception['name']]

                        if e.__class__.__name__ not in allowed_exception_names:
                            print('Wrong execption raised!')
                            raise

                        assert e.args[0] == allowed_exception['message']
                        return

                    raise

                if test_data.get('idempotent', True):
                    second_output_commands = unroll_generators(op._pyinfra_op(
                        *test_data.get('args', []),
                        **kwargs
                    ))
                    if second_output_commands:
                        raise Exception((
                            'Operation not idempotent, second output commands: {0}'
                        ).format(second_output_commands))

            commands = []

            for command in output_commands:
                if isinstance(command, six.string_types):  # matches pyinfra/api/operation.py
                    command = StringCommand(command.strip())

                if isinstance(command, StringCommand):
                    json_command = get_command_string(command)

                elif isinstance(command, dict):
                    command['command'] = get_command_string(command['command']).strip()
                    json_command = command

                elif isinstance(command, FunctionCommand):
                    func_name = (
                        command.function if command.function == '__func__'
                        else command.function.__name__
                    )
                    json_command = [
                        func_name, list(command.args), command.kwargs,
                    ]

                elif isinstance(command, FileUploadCommand):
                    if hasattr(command.src, 'read'):
                        command.src.seek(0)
                        data = command.src.read()
                    else:
                        data = command.src
                    json_command = ['upload', data, command.dest]

                elif isinstance(command, FileDownloadCommand):
                    json_command = ['download', command.src, command.dest]

                else:
                    raise Exception('{0} is not a valid command!'.format(command))

                if command.executor_kwargs:
                    command.executor_kwargs['command'] = json_command
                    json_command = command.executor_kwargs

                commands.append(json_command)

            try:
                assert commands == test_data['commands']
            except AssertionError as e:
                print()
                print('--> COMMANDS OUTPUT:')
                print(json.dumps(commands, indent=4, default=json_encode))

                print('--> TEST WANTS:')
                print(json.dumps(
                    test_data['commands'], indent=4, default=json_encode,
                ))

                raise e

            noop_description = test_data.get('noop_description')
            if len(commands) == 0 or noop_description:
                if noop_description is not None:
                    assert host.noop_description == noop_description
                else:
                    assert host.noop_description is not None, 'no noop description was set'
                    warnings.warn('No noop_description set for test: {0} (got "{1}")'.format(
                        test_name, host.noop_description,
                    ))

    return TestTests


# Find available operation tests
operations = sorted([
    filename
    for filename in listdir(path.join('tests', 'operations'))
    if path.isdir(path.join('tests', 'operations', filename))
])

# Generate the classes, attaching to locals so nose picks them up
for operation_name in operations:
    locals()[operation_name] = make_operation_tests(operation_name)
