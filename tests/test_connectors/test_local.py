import tempfile
from io import BytesIO, StringIO
from subprocess import PIPE
from unittest import TestCase
from unittest.mock import MagicMock, call, mock_open, patch

import gevent

from pyinfra.api import Config, HiddenValue, State, StringCommand
from pyinfra.api.connect import connect_all
from pyinfra.connectors.util import make_unix_command

from ..util import make_inventory


class FailingSink:
    """Binary sink whose writes always fail, mimicking a full disk."""

    def write(self, data):
        raise OSError(28, "No space left on device")

    def seekable(self):
        return False


@patch("pyinfra.connectors.local.mkstemp", lambda: (None, "__tempfile__"))
@patch("pyinfra.connectors.local.os.remove", lambda f: None)
@patch("pyinfra.connectors.local.open", mock_open(read_data="test!"), create=True)
@patch("pyinfra.api.util.open", mock_open(read_data="test!"), create=True)
class TestLocalConnector(TestCase):
    def setUp(self):
        self.fake_popen_patch = patch("pyinfra.connectors.util.Popen")
        self.fake_popen_mock = self.fake_popen_patch.start()

    def tearDown(self):
        self.fake_popen_patch.stop()

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
        self.fake_popen_mock().returncode = 0

        out = host.run_shell_command(command, _stdin="hello", print_output=True)
        assert len(out) == 2

        status, output = out
        assert status is True
        self.fake_popen_mock().stdin.write.assert_called_with(b"hello\n")

        combined_out = host.run_shell_command(
            command,
            _stdin="hello",
            print_output=True,
        )
        assert len(combined_out) == 2

        shell_command = make_unix_command(command).get_raw_value()
        self.fake_popen_mock.assert_called_with(
            shell_command,
            shell=True,
            stdout=PIPE,
            stderr=PIPE,
            stdin=PIPE,
        )

    @patch("pyinfra.api.output._echo")
    def test_run_shell_command_masked(self, fake_echo):
        inventory = make_inventory(hosts=("@local",))
        State(inventory, Config())
        host = inventory.get_host("@local")

        command = StringCommand("echo", HiddenValue("top-secret-stuff"))
        self.fake_popen_mock().returncode = 0

        out = host.run_shell_command(command, print_output=True, print_input=True)
        assert len(out) == 2

        status, output = out
        assert status is True

        self.fake_popen_mock.assert_called_with(
            "sh -c 'echo top-secret-stuff'",
            shell=True,
            stdout=PIPE,
            stderr=PIPE,
            stdin=PIPE,
        )

        fake_echo.assert_called_with(
            f"{host.print_prefix}>>> sh -c 'echo *MASKED*'",
            err=True,
        )

    def test_run_shell_command_success_exit_codes(self):
        inventory = make_inventory(hosts=("@local",))
        State(inventory, Config())
        host = inventory.get_host("@local")

        command = "echo hi"
        self.fake_popen_mock().returncode = 1

        out = host.run_shell_command(command, _success_exit_codes=[1])
        assert len(out) == 2
        assert out[0] is True

    def test_run_shell_command_error(self):
        inventory = make_inventory(hosts=("@local",))
        State(inventory, Config())
        host = inventory.get_host("@local")

        command = "echo hi"
        self.fake_popen_mock().returncode = 1

        out = host.run_shell_command(command)
        assert len(out) == 2
        assert out[0] is False

    def test_put_file(self):
        inventory = make_inventory(hosts=("@local",))
        State(inventory, Config())

        host = inventory.get_host("@local")

        fake_process = MagicMock(returncode=0)
        self.fake_popen_mock.return_value = fake_process

        host.put_file("not-a-file", "not-another-file", print_output=True)

        self.fake_popen_mock.assert_called_with(
            "sh -c 'cp __tempfile__ not-another-file'",
            shell=True,
            stdout=PIPE,
            stderr=PIPE,
            stdin=PIPE,
        )

    def test_put_file_with_spaces(self):
        inventory = make_inventory(hosts=("@local",))
        State(inventory, Config())

        host = inventory.get_host("@local")

        fake_process = MagicMock(returncode=0)
        self.fake_popen_mock.return_value = fake_process

        host.put_file("not-a-file", "not another file with spaces", print_output=True)

        self.fake_popen_mock.assert_called_with(
            "sh -c 'cp __tempfile__ '\"'\"'not another file with spaces'\"'\"''",
            shell=True,
            stdout=PIPE,
            stderr=PIPE,
            stdin=PIPE,
        )

    def test_put_file_error(self):
        inventory = make_inventory(hosts=("@local",))
        State(inventory, Config())

        host = inventory.get_host("@local")

        fake_process = MagicMock(returncode=1)
        self.fake_popen_mock.return_value = fake_process

        with self.assertRaises(IOError):
            host.put_file("not-a-file", "not-another-file", print_output=True)

    def test_get_file(self):
        inventory = make_inventory(hosts=("@local",))
        State(inventory, Config())

        host = inventory.get_host("@local")

        fake_process = MagicMock(returncode=0)
        self.fake_popen_mock.return_value = fake_process

        host.get_file("not-a-file", "not-another-file", print_output=True)

        self.fake_popen_mock.assert_called_with(
            "sh -c 'cp not-a-file __tempfile__'",
            shell=True,
            stdout=PIPE,
            stderr=PIPE,
            stdin=PIPE,
        )

    def test_get_file_error(self):
        inventory = make_inventory(hosts=("@local",))
        State(inventory, Config())

        host = inventory.get_host("@local")

        fake_process = MagicMock(returncode=1)
        self.fake_popen_mock.return_value = fake_process

        with self.assertRaises(IOError):
            host.get_file("not-a-file", "not-another-file", print_output=True)

    def test_write_stdin(self):
        inventory = make_inventory(hosts=("@local",))
        State(inventory, Config())
        host = inventory.get_host("@local")

        command = "echo Šablony"
        self.fake_popen_mock().returncode = 0

        host.run_shell_command(command, _stdin=["hello", "abc"], print_output=True)
        self.fake_popen_mock().stdin.write.assert_has_calls(
            [
                call(b"hello\n"),
                call(b"abc\n"),
            ],
        )

    def test_write_stdin_io_object(self):
        inventory = make_inventory(hosts=("@local",))
        State(inventory, Config())
        host = inventory.get_host("@local")

        command = "echo Šablony"
        self.fake_popen_mock().returncode = 0

        host.run_shell_command(command, _stdin=StringIO("hello\nabc"), print_output=True)
        self.fake_popen_mock().stdin.write.assert_has_calls(
            [
                call(b"hello\n"),
                call(b"abc\n"),
            ],
        )

    def test_write_stdin_bytes(self):
        inventory = make_inventory(hosts=("@local",))
        State(inventory, Config())
        host = inventory.get_host("@local")

        command = "cat > /dest"
        self.fake_popen_mock().returncode = 0

        host.run_shell_command(command, _stdin=b"\x00binary\xffno newline", print_output=True)
        self.fake_popen_mock().stdin.write.assert_called_with(b"\x00binary\xffno newline")

    def test_write_stdin_binary_io_object(self):
        inventory = make_inventory(hosts=("@local",))
        State(inventory, Config())
        host = inventory.get_host("@local")

        command = "cat > /dest"
        self.fake_popen_mock().returncode = 0

        payload = b"\x00binary\xffwith\nnewlines\n\x1b"
        host.run_shell_command(command, _stdin=BytesIO(payload), print_output=True)
        self.fake_popen_mock().stdin.write.assert_called_with(payload)

    def test_stdout_sink_streams_raw_bytes(self):
        inventory = make_inventory(hosts=("@local",))
        State(inventory, Config())
        host = inventory.get_host("@local")

        self.fake_popen_mock().returncode = 0
        payload = b"\x00binary\xffwith\nnewlines\n\x1b"
        self.fake_popen_mock().stdout.read.side_effect = [payload, b""]

        sink = BytesIO()
        status, output = host.run_shell_command("cat /src", _stdout=sink, print_output=True)

        assert status is True
        assert sink.getvalue() == payload
        # Diverted output is not decoded into the command result
        assert output.stdout_lines == []

    def test_stdout_sink_write_error_is_raised(self):
        inventory = make_inventory(hosts=("@local",))
        State(inventory, Config())
        host = inventory.get_host("@local")

        self.fake_popen_mock().returncode = 0
        self.fake_popen_mock().stdout.read.side_effect = [b"payload", b""]

        # A sink that cannot be written to must fail the command, not report success with a
        # truncated sink.
        with self.assertRaises(OSError):
            host.run_shell_command("cat /src", _stdout=FailingSink(), print_output=True)

    def test_stdout_sink_write_error_is_not_reported_as_a_timeout(self):
        inventory = make_inventory(hosts=("@local",))
        State(inventory, Config())
        host = inventory.get_host("@local")

        self.fake_popen_mock().returncode = 0
        self.fake_popen_mock().stdout.read.side_effect = [b"payload", b""]

        with self.assertRaises(OSError):
            host.run_shell_command(
                "cat /src",
                _stdout=FailingSink(),
                _timeout=5,
                print_output=True,
            )

    def test_stdout_sink_write_error_does_not_hang_on_a_blocked_reader(self):
        inventory = make_inventory(hosts=("@local",))
        State(inventory, Config())
        host = inventory.get_host("@local")

        self.fake_popen_mock().returncode = 0
        self.fake_popen_mock().stdout.read.side_effect = [b"payload", b""]

        def _blocking_iter():
            gevent.sleep(30)
            return iter([])

        # A failed sink stops draining stdout, so the stderr reader stays blocked on a
        # command that keeps writing: without killing it the call would hang here.
        self.fake_popen_mock().stderr.__iter__.side_effect = _blocking_iter

        with gevent.Timeout(10):
            with self.assertRaises(OSError):
                host.run_shell_command("cat /src", _stdout=FailingSink(), print_output=True)

    def test_write_stdin_binary_tempfile(self):
        inventory = make_inventory(hosts=("@local",))
        State(inventory, Config())
        host = inventory.get_host("@local")

        self.fake_popen_mock().returncode = 0
        payload = b"\x00binary\xffwith\nnewlines\n\x1b"

        # Tempfile wrappers are not RawIOBase/BufferedIOBase, but they are binary streams.
        with tempfile.SpooledTemporaryFile(mode="w+b") as spooled:
            spooled.write(payload)
            spooled.seek(0)
            host.run_shell_command("cat > /dest", _stdin=spooled, print_output=True)

        self.fake_popen_mock().stdin.write.assert_called_with(payload)

    def test_write_stdin_named_tempfile(self):
        inventory = make_inventory(hosts=("@local",))
        State(inventory, Config())
        host = inventory.get_host("@local")

        self.fake_popen_mock().returncode = 0
        payload = b"\x00binary\xffpayload"

        with tempfile.NamedTemporaryFile() as named:
            named.write(payload)
            named.seek(0)
            host.run_shell_command("cat > /dest", _stdin=named, print_output=True)

        self.fake_popen_mock().stdin.write.assert_called_with(payload)

    def test_write_stdin_text_tempfile_keeps_line_handling(self):
        inventory = make_inventory(hosts=("@local",))
        State(inventory, Config())
        host = inventory.get_host("@local")

        self.fake_popen_mock().returncode = 0

        # Text mode tempfiles have an `encoding` and must keep the line based handling.
        with tempfile.SpooledTemporaryFile(mode="w+") as spooled:
            spooled.write("hello")
            spooled.seek(0)
            host.run_shell_command("cat > /dest", _stdin=spooled, print_output=True)

        self.fake_popen_mock().stdin.write.assert_called_with(b"hello\n")

    def test_write_stdin_bytearray_and_memoryview(self):
        inventory = make_inventory(hosts=("@local",))
        State(inventory, Config())
        host = inventory.get_host("@local")

        self.fake_popen_mock().returncode = 0
        payload = b"\x00binary\xffpayload"

        host.run_shell_command("cat > /dest", _stdin=bytearray(payload), print_output=True)
        self.fake_popen_mock().stdin.write.assert_called_with(payload)

        self.fake_popen_mock().stdin.write.reset_mock()
        host.run_shell_command("cat > /dest", _stdin=memoryview(payload), print_output=True)
        self.fake_popen_mock().stdin.write.assert_called_with(payload)

    def test_write_stdin_empty_payloads(self):
        inventory = make_inventory(hosts=("@local",))
        State(inventory, Config())
        host = inventory.get_host("@local")

        self.fake_popen_mock().returncode = 0

        # Empty bytes are a real payload, e.g. truncating a remote file.
        host.run_shell_command("cat > /dest", _stdin=b"", print_output=True)
        self.fake_popen_mock().stdin.write.assert_called_with(b"")

        # The empty *text* payload keeps its historical no-op behaviour.
        self.fake_popen_mock().stdin.write.reset_mock()
        host.run_shell_command("cat > /dest", _stdin="", print_output=True)
        self.fake_popen_mock().stdin.write.assert_not_called()
