from unittest import TestCase
from unittest.mock import AsyncMock, mock_open, patch

from pyinfra.api import Config, QuoteString, State, StringCommand
from pyinfra.api.connect import connect_all
from pyinfra.api.exceptions import InventoryError, PyinfraError
from pyinfra.connectors.util import CommandOutput, OutputLine, make_unix_command

from ..util import make_inventory


class TestContainerConnector(TestCase):
    # we use this class as a template to prevent the decorators from being invoked twice on
    # the podman test class (since it needs to override fake_docker_shell)
    __test__ = False  # this class should not be tested.
    cli_cmd = "docker"
    connector_name = "docker"

    def setUp(self):
        self.command_handlers: list[tuple[callable, callable]] = []

        self.local_connect_patch = patch(
            "pyinfra.connectors.docker.LocalConnector.connect",
            new_callable=AsyncMock,
        )
        self.local_connect = self.local_connect_patch.start()
        self.local_connect.return_value = None

        self.local_run_shell_patch = patch(
            "pyinfra.connectors.docker.LocalConnector.run_shell_command",
            new_callable=AsyncMock,
        )
        self.local_run_shell = self.local_run_shell_patch.start()

        async def _run_shell_side_effect(command: StringCommand, *args, **kwargs):
            for predicate, handler in self.command_handlers:
                if predicate(command):
                    result = handler(command)
                    if isinstance(result, Exception):
                        raise result
                    return result
            return self._success()

        self.local_run_shell.side_effect = _run_shell_side_effect

        self._prepare_default_container()

    def tearDown(self):
        self.local_run_shell_patch.stop()
        self.local_connect_patch.stop()

    def test_missing_image(self):
        with self.assertRaises(InventoryError):
            make_inventory(hosts=(f"@{self.connector_name}",))

    def test_user_provided_container_id(self):
        inventory = make_inventory(
            hosts=((f"@{self.connector_name}/not-an-image", {"docker_container_id": "abc"}),),
        )
        State(inventory, Config())
        host = inventory.get_host(f"@{self.connector_name}/not-an-image")
        host.connect()
        assert host.data.docker_container_id == "abc"

    def test_connect_all(self):
        inventory = make_inventory(hosts=(f"@{self.connector_name}/not-an-image",))
        state = State(inventory, Config())
        connect_all(state)
        assert len(state.active_hosts) == 1

    def test_connect_all_error(self):
        inventory = make_inventory(hosts=(f"@{self.connector_name}/a-broken-image",))
        state = State(inventory, Config())

        self._prepare_failed_container("a-broken-image")

        with self.assertRaises(PyinfraError):
            connect_all(state)

    def test_connect_disconnect_host(self):
        inventory = make_inventory(hosts=(f"@{self.connector_name}/not-an-image",))
        state = State(inventory, Config())
        host = inventory.get_host(f"@{self.connector_name}/not-an-image")
        host.connect(reason=True)
        assert len(state.active_hosts) == 0
        host.disconnect()

    def test_run_shell_command(self):
        inventory = make_inventory(hosts=(f"@{self.connector_name}/not-an-image",))
        State(inventory, Config())

        command = "echo hi"
        host = inventory.get_host(f"@{self.connector_name}/not-an-image")
        host.connect()
        out = host.run_shell_command(
            command,
            _stdin="hello",
            _get_pty=True,
            print_output=True,
        )
        assert len(out) == 2
        assert out[0] is True
        exec_call = self._find_exec_call()
        assert exec_call is not None
        exec_command, kwargs = exec_call
        exec_bits = tuple(exec_command.bits)
        assert exec_bits[0:2] == (self.cli_cmd, "exec")
        assert exec_bits[2] in ("-it", "-i")
        assert exec_bits[3] == "containerid"
        assert exec_bits[4:6] == ("sh", "-c")
        inner = exec_command.bits[6]
        assert isinstance(inner, StringCommand)
        inner_bits = tuple(inner.bits)
        assert len(inner_bits) == 1
        quoted = inner_bits[0]
        assert isinstance(quoted, QuoteString)
        assert isinstance(quoted.obj, StringCommand)
        assert (
            quoted.obj.get_raw_value() == make_unix_command(StringCommand(command)).get_raw_value()
        )
        assert kwargs.get("print_output") is True

    def test_run_shell_command_success_exit_codes(self):
        inventory = make_inventory(hosts=(f"@{self.connector_name}/not-an-image",))
        State(inventory, Config())

        command = "echo hi"
        host = inventory.get_host(f"@{self.connector_name}/not-an-image")
        host.connect()
        self._set_exec_result(success=True)
        out = host.run_shell_command(command, _success_exit_codes=[1])
        assert out[0] is True

    def test_run_shell_command_error(self):
        inventory = make_inventory(hosts=(f"@{self.connector_name}/not-an-image",))
        State(inventory, Config())
        command = "echo hi"
        host = inventory.get_host(f"@{self.connector_name}/not-an-image")
        host.connect()
        self._set_exec_result(success=False)
        out = host.run_shell_command(command)
        assert out[0] is False

    def test_put_file(self):
        inventory = make_inventory(hosts=(f"@{self.connector_name}/not-an-image",))
        State(inventory, Config())

        host = inventory.get_host(f"@{self.connector_name}/not-an-image")
        host.connect()

        host.put_file("not-a-file", "not-another-file", print_output=True)
        cp_call = self._find_last_call(
            lambda cmd: tuple(cmd.bits[:3]) == (self.cli_cmd, "cp", "__tempfile__"),
        )
        assert cp_call is not None
        cp_command, kwargs = cp_call
        assert tuple(cp_command.bits) == (
            self.cli_cmd,
            "cp",
            "__tempfile__",
            "containerid:not-another-file",
        )
        assert kwargs.get("print_output") is True

    def test_put_file_error(self):
        inventory = make_inventory(hosts=(f"@{self.connector_name}/not-an-image",))
        State(inventory, Config())

        host = inventory.get_host(f"@{self.connector_name}/not-an-image")
        host.connect()
        self._add_command_response(
            self._match_command(self.cli_cmd, "cp", "__tempfile__", "containerid:not-another-file"),
            (False, self._stderr_output("cp error")),
        )

        with self.assertRaises(IOError):
            host.put_file("not-a-file", "not-another-file", print_output=True)

    def test_get_file(self):
        inventory = make_inventory(hosts=(f"@{self.connector_name}/not-an-image",))
        State(inventory, Config())

        host = inventory.get_host(f"@{self.connector_name}/not-an-image")
        host.connect()

        host.get_file("not-a-file", "not-another-file", print_output=True)
        cp_call = self._find_last_call(
            lambda cmd: tuple(cmd.bits[:3]) == (self.cli_cmd, "cp", "containerid:not-a-file"),
        )
        assert cp_call is not None
        cp_command, kwargs = cp_call
        assert tuple(cp_command.bits) == (
            self.cli_cmd,
            "cp",
            "containerid:not-a-file",
            "__tempfile__",
        )
        assert kwargs.get("print_output") is True

    def test_get_file_error(self):
        inventory = make_inventory(hosts=(f"@{self.connector_name}/not-an-image",))
        State(inventory, Config())

        host = inventory.get_host(f"@{self.connector_name}/not-an-image")
        host.connect()
        self._add_command_response(
            self._match_command(self.cli_cmd, "cp", "containerid:not-a-file", "__tempfile__"),
            (False, self._stderr_output("cp error")),
        )

        with self.assertRaises(IOError):
            host.get_file("not-a-file", "not-another-file", print_output=True)

    # Helpers

    def _stdout_output(self, *lines: str) -> CommandOutput:
        return CommandOutput([OutputLine("stdout", line) for line in lines if line != ""])

    def _stderr_output(self, *lines: str) -> CommandOutput:
        return CommandOutput([OutputLine("stderr", line) for line in lines if line != ""])

    def _success(self) -> tuple[bool, CommandOutput]:
        return True, CommandOutput([])

    def _match_command(self, *bits):
        def predicate(command: StringCommand) -> bool:
            return tuple(command.bits) == bits

        return predicate

    def _add_command_response(self, predicate, result):
        def handler(_command):
            return result

        self.command_handlers.append((predicate, handler))

    def _prepare_default_container(self, identifier: str = "not-an-image") -> None:
        self._add_command_response(
            self._match_command(self.cli_cmd, "container", "inspect", identifier),
            (False, self._stderr_output("no such container")),
        )
        self._add_command_response(
            self._match_command(self.cli_cmd, "run", "-d", identifier, "tail", "-f", "/dev/null"),
            (True, self._stdout_output("containerid")),
        )
        self._add_command_response(
            self._match_command(self.cli_cmd, "commit", "containerid"),
            (True, self._stdout_output("sha256:blahsomerandomstringdata")),
        )
        self._add_command_response(
            self._match_command(self.cli_cmd, "rm", "-f", "containerid"),
            self._success(),
        )

    def _prepare_failed_container(self, identifier: str) -> None:
        self._add_command_response(
            self._match_command(self.cli_cmd, "container", "inspect", identifier),
            (False, self._stderr_output("inspect failed")),
        )
        self._add_command_response(
            self._match_command(self.cli_cmd, "run", "-d", identifier, "tail", "-f", "/dev/null"),
            (False, self._stderr_output("run failed")),
        )

    def _find_last_call(self, predicate):
        for entry in reversed(self.local_run_shell.await_args_list):
            command = entry.args[0]
            kwargs = entry.kwargs
            if predicate(command):
                return command, kwargs
        return None

    def _find_exec_call(self):
        return self._find_last_call(
            lambda cmd: len(cmd.bits) >= 6 and tuple(cmd.bits[:2]) == (self.cli_cmd, "exec"),
        )

    def _set_exec_result(self, success: bool):
        def handler(_command: StringCommand):
            if success:
                return True, CommandOutput([])
            return False, self._stderr_output("exec failed")

        def predicate(command: StringCommand) -> bool:
            bits = tuple(command.bits[:2])
            return len(command.bits) >= 6 and bits == (self.cli_cmd, "exec")

        self.command_handlers.append((predicate, handler))


@patch("pyinfra.connectors.docker.mkstemp", lambda: (None, "__tempfile__"))
@patch("pyinfra.connectors.docker.os.remove", lambda f: None)
@patch("pyinfra.connectors.docker.os.close", lambda f: None)
@patch("pyinfra.connectors.docker.open", mock_open(read_data="test!"), create=True)
@patch("pyinfra.api.util.open", mock_open(read_data="test!"), create=True)
class TestDocker2Connector(TestContainerConnector):
    __test__ = True
    cli_cmd = "docker"
    connector_name = "docker"


@patch("pyinfra.connectors.docker.mkstemp", lambda: (None, "__tempfile__"))
@patch("pyinfra.connectors.docker.os.remove", lambda f: None)
@patch("pyinfra.connectors.docker.os.close", lambda f: None)
@patch("pyinfra.connectors.docker.open", mock_open(read_data="test!"), create=True)
@patch("pyinfra.api.util.open", mock_open(read_data="test!"), create=True)
class TestPodmanConnector(TestContainerConnector):
    __test__ = True
    cli_cmd = "podman"
    connector_name = "podman"
