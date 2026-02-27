# encoding: utf-8

from asyncio.subprocess import PIPE
from io import StringIO
from unittest import TestCase
from unittest.mock import AsyncMock, MagicMock, call, mock_open, patch

from pyinfra.api import Config, MaskString, State, StringCommand
from pyinfra.api.connect import connect_all
from pyinfra.connectors.util import make_unix_command

from ..util import make_inventory


@patch("pyinfra.connectors.local.mkstemp", lambda: (None, "__tempfile__"))
@patch("pyinfra.connectors.local.os.remove", lambda f: None)
@patch("pyinfra.connectors.local.open", mock_open(read_data="test!"), create=True)
@patch("pyinfra.api.util.open", mock_open(read_data="test!"), create=True)
class TestLocalConnector(TestCase):
    def setUp(self):
        self.process_mock = MagicMock()
        self.process_mock.communicate = AsyncMock(return_value=(b"", b""))
        self.process_mock.kill = MagicMock()
        self.process_mock.returncode = 0

        self.create_subprocess_patch = patch(
            "pyinfra.connectors.util.asyncio.create_subprocess_shell",
            new_callable=AsyncMock,
        )
        self.create_subprocess_mock = self.create_subprocess_patch.start()
        self.create_subprocess_mock.return_value = self.process_mock

    def tearDown(self):
        self.create_subprocess_patch.stop()

    def test_connect_all(self):
        inventory = make_inventory(hosts=("@local",))
        state = State(inventory, Config())
        connect_all(state)
        assert len(state.active_hosts) == 1

    def test_connect_host(self):
        inventory = make_inventory(hosts=("@local",))
        state = State(inventory, Config())
        host = inventory.get_host("@local")
        host.connect(reason=True)
        assert len(state.active_hosts) == 0

    def test_run_shell_command(self):
        inventory = make_inventory(hosts=("@local",))
        State(inventory, Config())
        host = inventory.get_host("@local")

        command = "echo Šablony"
        self.process_mock.returncode = 0
        self.process_mock.communicate.return_value = ("Šablony\n".encode("utf-8"), b"")

        out = host.run_shell_command(command, _stdin="hello", print_output=True)
        assert len(out) == 2

        status, output = out
        assert status is True
        assert self.process_mock.communicate.await_args_list[0] == call(b"hello\n")

        combined_out = host.run_shell_command(
            command,
            _stdin="hello",
            print_output=True,
        )
        assert len(combined_out) == 2

        shell_command = make_unix_command(command).get_raw_value()
        assert self.create_subprocess_mock.await_args_list[-1] == call(
            shell_command,
            stdout=PIPE,
            stderr=PIPE,
            stdin=PIPE,
        )

    @patch("pyinfra.connectors.local.click")
    def test_run_shell_command_masked(self, fake_click):
        inventory = make_inventory(hosts=("@local",))
        State(inventory, Config())
        host = inventory.get_host("@local")

        command = StringCommand("echo", MaskString("top-secret-stuff"))
        self.process_mock.returncode = 0
        self.process_mock.communicate.return_value = (b"top-secret-stuff\n", b"")

        out = host.run_shell_command(command, print_output=True, print_input=True)
        assert len(out) == 2

        status, output = out
        assert status is True

        assert self.create_subprocess_mock.await_args_list[-1] == call(
            "sh -c 'echo top-secret-stuff'",
            stdout=PIPE,
            stderr=PIPE,
            stdin=PIPE,
        )

        fake_click.echo.assert_called_with(
            "{0}>>> sh -c 'echo ***'".format(host.print_prefix),
            err=True,
        )

    def test_run_shell_command_success_exit_codes(self):
        inventory = make_inventory(hosts=("@local",))
        State(inventory, Config())
        host = inventory.get_host("@local")

        command = "echo hi"
        self.process_mock.returncode = 1

        out = host.run_shell_command(command, _success_exit_codes=[1])
        assert len(out) == 2
        assert out[0] is True

    def test_run_shell_command_error(self):
        inventory = make_inventory(hosts=("@local",))
        State(inventory, Config())
        host = inventory.get_host("@local")

        command = "echo hi"
        self.process_mock.returncode = 1

        out = host.run_shell_command(command)
        assert len(out) == 2
        assert out[0] is False

    def test_put_file(self):
        inventory = make_inventory(hosts=("@local",))
        State(inventory, Config())

        host = inventory.get_host("@local")

        self.process_mock.returncode = 0
        self.process_mock.communicate.return_value = (b"", b"")

        host.put_file("not-a-file", "not-another-file", print_output=True)

        assert self.create_subprocess_mock.await_args_list[-1] == call(
            "sh -c 'cp __tempfile__ not-another-file'",
            stdout=PIPE,
            stderr=PIPE,
            stdin=PIPE,
        )

    def test_put_file_with_spaces(self):
        inventory = make_inventory(hosts=("@local",))
        State(inventory, Config())

        host = inventory.get_host("@local")

        self.process_mock.returncode = 0
        self.process_mock.communicate.return_value = (b"", b"")

        host.put_file("not-a-file", "not another file with spaces", print_output=True)

        assert self.create_subprocess_mock.await_args_list[-1] == call(
            "sh -c 'cp __tempfile__ '\"'\"'not another file with spaces'\"'\"''",
            stdout=PIPE,
            stderr=PIPE,
            stdin=PIPE,
        )

    def test_put_file_error(self):
        inventory = make_inventory(hosts=("@local",))
        State(inventory, Config())

        host = inventory.get_host("@local")

        self.process_mock.returncode = 1
        self.process_mock.communicate.return_value = (b"", b"cp error\n")

        with self.assertRaises(IOError):
            host.put_file("not-a-file", "not-another-file", print_output=True)

    def test_get_file(self):
        inventory = make_inventory(hosts=("@local",))
        State(inventory, Config())

        host = inventory.get_host("@local")

        self.process_mock.returncode = 0
        self.process_mock.communicate.return_value = (b"", b"")

        host.get_file("not-a-file", "not-another-file", print_output=True)

        assert self.create_subprocess_mock.await_args_list[-1] == call(
            "sh -c 'cp not-a-file __tempfile__'",
            stdout=PIPE,
            stderr=PIPE,
            stdin=PIPE,
        )

    def test_get_file_error(self):
        inventory = make_inventory(hosts=("@local",))
        State(inventory, Config())

        host = inventory.get_host("@local")

        self.process_mock.returncode = 1
        self.process_mock.communicate.return_value = (b"", b"cp error\n")

        with self.assertRaises(IOError):
            host.get_file("not-a-file", "not-another-file", print_output=True)

    def test_write_stdin(self):
        inventory = make_inventory(hosts=("@local",))
        State(inventory, Config())
        host = inventory.get_host("@local")

        command = "echo Šablony"
        self.process_mock.returncode = 0
        self.process_mock.communicate.return_value = ("Šablony\n".encode("utf-8"), b"")

        host.run_shell_command(command, _stdin=["hello", "abc"], print_output=True)
        assert self.process_mock.communicate.await_args_list[-1] == call(b"hello\nabc\n")

    def test_write_stdin_io_object(self):
        inventory = make_inventory(hosts=("@local",))
        State(inventory, Config())
        host = inventory.get_host("@local")

        command = "echo Šablony"
        self.process_mock.returncode = 0
        self.process_mock.communicate.return_value = ("Šablony\n".encode("utf-8"), b"")

        host.run_shell_command(command, _stdin=StringIO("hello\nabc"), print_output=True)
        assert self.process_mock.communicate.await_args_list[-1] == call(b"hello\nabc\n")
