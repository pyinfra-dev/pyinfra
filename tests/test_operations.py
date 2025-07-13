import json
import platform
import warnings
from importlib import import_module
from os import listdir, path
from unittest import TestCase
from unittest.mock import patch

from pyinfra.api import FileDownloadCommand, FileUploadCommand, FunctionCommand, StringCommand
from pyinfra.context import ctx_host, ctx_state
from pyinfra_cli.util import json_encode

from .util import FakeState, YamlTest, create_host, get_command_string, parse_value, patch_files

PLATFORM_NAME = platform.system()


def parse_commands(commands):
    json_commands = []

    for command in commands:
        if isinstance(command, str):  # matches pyinfra/api/operation.py
            command = StringCommand(command.strip())

        if isinstance(command, StringCommand):
            json_command = get_command_string(command)

        elif isinstance(command, dict):
            command["command"] = get_command_string(command["command"]).strip()
            json_command = command

        elif isinstance(command, FunctionCommand):
            func_name = (
                command.function if command.function == "__func__" else command.function.__name__
            )
            json_command = [
                func_name,
                list(command.args),
                command.kwargs,
            ]

        elif isinstance(command, FileUploadCommand):
            if hasattr(command.src, "read"):
                command.src.seek(0)
                data = command.src.read()
                if isinstance(data, bytes):
                    data = data.decode()
            else:
                data = str(command.src)
            json_command = ["upload", data, str(command.dest)]

        elif isinstance(command, FileDownloadCommand):
            json_command = ["download", str(command.src), str(command.dest)]

        else:
            raise Exception("{0} is not a valid command!".format(command))

        if command.connector_arguments:
            command.connector_arguments["command"] = json_command
            json_command = command.connector_arguments

        json_commands.append(json_command)
    return json_commands


def assert_commands(commands, wanted_commands):
    try:
        assert commands == wanted_commands
    except AssertionError as e:
        print()
        print("--> COMMANDS OUTPUT:")
        print(json.dumps(commands, indent=4, default=json_encode))

        print("--> TEST WANTS:")
        print(
            json.dumps(
                wanted_commands,
                indent=4,
                default=json_encode,
            ),
        )

        raise e


def make_operation_tests(arg):
    # Get the operation we're testing against
    module_name, op_name = arg.rsplit(".", 1)
    module = import_module("pyinfra.operations.{0}".format(module_name))
    op = getattr(module, op_name)

    # Generate a test class
    @patch("pyinfra.operations.files.get_timestamp", lambda: "a-timestamp")
    @patch("pyinfra.operations.util.files.get_timestamp", lambda: "a-timestamp")
    class TestTests(TestCase, metaclass=YamlTest):
        yaml_test_dir = path.join("tests", "operations", arg)
        yaml_test_prefix = "test_{0}_{1}_".format(module_name, op_name)

        @classmethod
        def setUpClass(cls):
            # Create a global fake state that attach to context state
            cls.state = FakeState()

        def yaml_test_function(self, test_name, test_data):
            if (
                "require_platform" in test_data
                and PLATFORM_NAME not in test_data["require_platform"]
            ):
                return

            op_test_name = "{0}/{1}.json".format(arg, test_name)

            # Create a host with this tests facts and attach to context host
            host = create_host(self.state, facts=test_data.get("facts", {}))

            allowed_exception = test_data.get("exception")

            args = parse_value(test_data.get("args", []))
            kwargs = parse_value(test_data.get("kwargs", {}))

            with ctx_state.use(self.state):
                with ctx_host.use(host):
                    with patch_files(test_data.get("local_files", {})):
                        try:
                            output_commands = list(op._inner(*args, **kwargs))
                        except Exception as e:
                            if allowed_exception:
                                allowed_exception_names = allowed_exception.get("names")
                                if not allowed_exception_names:
                                    allowed_exception_names = [allowed_exception["name"]]

                                if e.__class__.__name__ not in allowed_exception_names:
                                    print("Wrong exception raised!")
                                    raise

                                assert e.args[0] == allowed_exception["message"]
                                return

                            raise

            commands = parse_commands(output_commands)
            assert_commands(commands, test_data["commands"])

            noop_description = test_data.get("noop_description")
            if len(commands) == 0 or noop_description:
                if noop_description is not None:
                    assert host.noop_description == noop_description
                else:
                    assert host.noop_description is not None, "no noop description was set"
                    warnings.warn(
                        'No noop_description set for test: {0} (got "{1}")'.format(
                            op_test_name,
                            host.noop_description,
                        ),
                    )

    return TestTests


# Find available operation tests
operations = sorted(
    [
        filename
        for filename in listdir(path.join("tests", "operations"))
        if path.isdir(path.join("tests", "operations", filename))
    ],
)

# Generate the classes, attaching to locals so nose picks them up
for operation_name in operations:
    locals()[operation_name] = make_operation_tests(operation_name)
