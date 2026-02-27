# encoding: utf-8

from unittest import TestCase
from unittest.mock import AsyncMock, mock_open, patch

from pyinfra.api import Config, QuoteString, State, StringCommand
from pyinfra.api.connect import connect_all
from pyinfra.api.exceptions import PyinfraError
from pyinfra.connectors.util import CommandOutput, OutputLine, make_unix_command

from ..util import make_inventory


@patch("pyinfra.connectors.chroot.mkstemp", lambda: (None, "__tempfile__"))
@patch("pyinfra.connectors.chroot.os.remove", lambda f: None)
@patch("pyinfra.connectors.chroot.open", mock_open(read_data="test!"), create=True)
@patch("pyinfra.api.util.open", mock_open(read_data="test!"), create=True)
class TestChrootConnector(TestCase):
    def setUp(self):
        self.local_connect_patch = patch(
            "pyinfra.connectors.chroot.LocalConnector.connect",
            new_callable=AsyncMock,
        )
        self.local_connect = self.local_connect_patch.start()

        self.local_run_shell_patch = patch(
            "pyinfra.connectors.chroot.LocalConnector.run_shell_command",
            new_callable=AsyncMock,
        )
        self.local_run_shell = self.local_run_shell_patch.start()
        self.local_run_shell.return_value = (True, CommandOutput([]))

    def tearDown(self):
        self.local_run_shell_patch.stop()
        self.local_connect_patch.stop()

    @staticmethod
    def _make_error_output(message: str) -> CommandOutput:
        return CommandOutput([OutputLine("stderr", message)])

    def test_connect_all(self):
        inventory = make_inventory(hosts=("@chroot/not-a-chroot",))
        state = State(inventory, Config())
        connect_all(state)
        assert len(state.active_hosts) == 1

    def test_connect_host(self):
        inventory = make_inventory(hosts=("@chroot/not-a-chroot",))
        state = State(inventory, Config())
        host = inventory.get_host("@chroot/not-a-chroot")
        host.connect(reason=True)
        assert len(state.active_hosts) == 0

    def test_connect_all_error(self):
        inventory = make_inventory(hosts=("@chroot/a-broken-chroot",))
        state = State(inventory, Config())

        self.local_run_shell.return_value = (False, self._make_error_output("failed"))

        with self.assertRaises(PyinfraError):
            connect_all(state)

    def test_run_shell_command(self):
        inventory = make_inventory(hosts=("@chroot/not-a-chroot",))
        State(inventory, Config())
        host = inventory.get_host("@chroot/not-a-chroot")
        host.connect()

        command = "echo hoi"
        self.local_run_shell.return_value = (True, CommandOutput([]))
        out = host.run_shell_command(
            command,
            _stdin="hello",
            _get_pty=True,
            print_output=True,
        )
        assert len(out) == 2
        assert out[0] is True

        unix_command = make_unix_command(command).get_raw_value()
        quoted = QuoteString(unix_command)
        expected_command = StringCommand(
            "chroot",
            "/not-a-chroot",
            "sh",
            "-c",
            quoted,
        )
        last_call = self.local_run_shell.await_args_list[-1]
        called_command = last_call.args[0]
        assert called_command.get_raw_value() == expected_command.get_raw_value()
        assert last_call.kwargs.get("print_output") is True

    def test_run_shell_command_success_exit_codes(self):
        inventory = make_inventory(hosts=("@chroot/not-a-chroot",))
        state = State(inventory, Config())
        connect_all(state)

        host = inventory.get_host("@chroot/not-a-chroot")

        command = "echo hoi"
        self.local_run_shell.return_value = (True, CommandOutput([]))

        out = host.run_shell_command(command, _success_exit_codes=[1])
        assert len(out) == 2
        assert out[0] is True

    def test_run_shell_command_error(self):
        inventory = make_inventory(hosts=("@chroot/not-a-chroot",))
        state = State(inventory, Config())
        connect_all(state)

        host = inventory.get_host("@chroot/not-a-chroot")

        command = "echo hoi"
        self.local_run_shell.return_value = (False, CommandOutput([]))

        out = host.run_shell_command(command)
        assert len(out) == 2
        assert out[0] is False

    def test_put_file(self):
        inventory = make_inventory(hosts=("@chroot/not-a-chroot",))
        state = State(inventory, Config())
        connect_all(state)

        host = inventory.get_host("@chroot/not-a-chroot")

        self.local_run_shell.return_value = (True, CommandOutput([]))

        host.put_file("not-a-file", "not-another-file", print_output=True)

        last_call = self.local_run_shell.await_args_list[-1]
        called_command = last_call.args[0]
        assert called_command.get_raw_value() == "cp __tempfile__ /not-a-chroot/not-another-file"
        assert last_call.kwargs.get("print_output") is True

    def test_put_file_error(self):
        inventory = make_inventory(hosts=("@chroot/not-a-chroot",))
        state = State(inventory, Config())
        connect_all(state)

        host = inventory.get_host("@chroot/not-a-chroot")

        self.local_run_shell.return_value = (False, self._make_error_output("cp error"))

        with self.assertRaises(IOError):
            host.put_file("not-a-file", "not-another-file", print_output=True)

    def test_get_file(self):
        inventory = make_inventory(hosts=("@chroot/not-a-chroot",))
        state = State(inventory, Config())
        connect_all(state)

        host = inventory.get_host("@chroot/not-a-chroot")

        self.local_run_shell.return_value = (True, CommandOutput([]))

        host.get_file("not-a-file", "not-another-file", print_output=True)

        last_call = self.local_run_shell.await_args_list[-1]
        called_command = last_call.args[0]
        assert called_command.get_raw_value() == "cp /not-a-chroot/not-a-file __tempfile__"
        assert last_call.kwargs.get("print_output") is True

    def test_get_file_error(self):
        inventory = make_inventory(hosts=("@chroot/not-a-chroot",))
        state = State(inventory, Config())
        connect_all(state)

        host = inventory.get_host("@chroot/not-a-chroot")

        self.local_run_shell.return_value = (False, self._make_error_output("cp error"))

        with self.assertRaises(IOError):
            host.get_file("not-a-file", "not-another-file", print_output=True)
