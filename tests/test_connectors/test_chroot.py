import asyncio
import shlex
from asyncio.subprocess import PIPE
from unittest import TestCase
from unittest.mock import mock_open, patch

from pyinfra.api import Config, State
from pyinfra.api.connect import connect_all
from pyinfra.api.exceptions import PyinfraError
from pyinfra.connectors.util import LOCAL_PROCESS_LINE_LIMIT, make_unix_command

from ..fake_subprocess import FakeSubprocess
from ..util import make_inventory


def fake_chroot_shell(command, splitlines=None):
    if command == "chroot /not-a-chroot ls":
        return True

    raise PyinfraError(f"Invalid command: {command}")


@patch("pyinfra.connectors.chroot.local.shell", fake_chroot_shell)
@patch("pyinfra.connectors.chroot.mkstemp", lambda: (None, "__tempfile__"))
@patch("pyinfra.connectors.chroot.os.remove", lambda f: None)
@patch("pyinfra.connectors.chroot.open", mock_open(read_data="test!"), create=True)
@patch("pyinfra.api.util.open", mock_open(read_data="test!"), create=True)
class TestChrootConnector(TestCase):
    def setUp(self):
        self.fake_subprocess = FakeSubprocess()
        self.fake_popen_patch = patch(
            "pyinfra.connectors.util.asyncio.create_subprocess_shell",
            self.fake_subprocess.mock,
        )
        self.fake_popen_mock = self.fake_popen_patch.start()

    def tearDown(self):
        self.fake_popen_patch.stop()

    def test_connect_all(self):
        inventory = make_inventory(hosts=("@chroot/not-a-chroot",))
        state = State(inventory, Config())
        asyncio.run(connect_all(state))
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

        with self.assertRaises(PyinfraError):
            asyncio.run(connect_all(state))

    def test_run_shell_command(self):
        inventory = make_inventory(hosts=("@chroot/not-a-chroot",))
        State(inventory, Config())
        host = inventory.get_host("@chroot/not-a-chroot")
        host.connect()

        command = "echo hoi"
        self.fake_subprocess.returncode = 0
        out = host.run_shell_command(
            command,
            _stdin="hello",
            _get_pty=True,
            print_output=True,
        )
        assert len(out) == 2
        assert out[0] is True

        command = make_unix_command(command).get_raw_value()
        command = shlex.quote(command)
        docker_command = f"chroot /not-a-chroot sh -c {command}"
        shell_command = make_unix_command(docker_command).get_raw_value()

        self.fake_popen_mock.assert_called_with(
            shell_command,
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
            limit=LOCAL_PROCESS_LINE_LIMIT,
        )

    def test_run_shell_command_success_exit_codes(self):
        inventory = make_inventory(hosts=("@chroot/not-a-chroot",))
        state = State(inventory, Config())
        asyncio.run(connect_all(state))

        host = inventory.get_host("@chroot/not-a-chroot")

        command = "echo hoi"
        self.fake_subprocess.returncode = 1

        out = host.run_shell_command(command, _success_exit_codes=[1])
        assert len(out) == 2
        assert out[0] is True

    def test_run_shell_command_error(self):
        inventory = make_inventory(hosts=("@chroot/not-a-chroot",))
        state = State(inventory, Config())
        asyncio.run(connect_all(state))

        host = inventory.get_host("@chroot/not-a-chroot")

        command = "echo hoi"
        self.fake_subprocess.returncode = 1

        out = host.run_shell_command(command)
        assert len(out) == 2
        assert out[0] is False

    def test_put_file(self):
        inventory = make_inventory(hosts=("@chroot/not-a-chroot",))
        state = State(inventory, Config())
        asyncio.run(connect_all(state))

        host = inventory.get_host("@chroot/not-a-chroot")

        self.fake_subprocess.returncode = 0

        host.put_file("not-a-file", "not-another-file", print_output=True)

        self.fake_popen_mock.assert_called_with(
            "sh -c 'cp __tempfile__ /not-a-chroot/not-another-file'",
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
            limit=LOCAL_PROCESS_LINE_LIMIT,
        )

    def test_put_file_error(self):
        inventory = make_inventory(hosts=("@chroot/not-a-chroot",))
        state = State(inventory, Config())
        asyncio.run(connect_all(state))

        host = inventory.get_host("@chroot/not-a-chroot")

        self.fake_subprocess.returncode = 1

        with self.assertRaises(IOError):
            host.put_file("not-a-file", "not-another-file", print_output=True)

    def test_get_file(self):
        inventory = make_inventory(hosts=("@chroot/not-a-chroot",))
        state = State(inventory, Config())
        asyncio.run(connect_all(state))

        host = inventory.get_host("@chroot/not-a-chroot")

        self.fake_subprocess.returncode = 0

        host.get_file("not-a-file", "not-another-file", print_output=True)

        self.fake_popen_mock.assert_called_with(
            "sh -c 'cp /not-a-chroot/not-a-file __tempfile__'",
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
            limit=LOCAL_PROCESS_LINE_LIMIT,
        )

    def test_get_file_error(self):
        inventory = make_inventory(hosts=("@chroot/not-a-chroot",))
        state = State(inventory, Config())
        asyncio.run(connect_all(state))

        host = inventory.get_host("@chroot/not-a-chroot")

        self.fake_subprocess.returncode = 1

        with self.assertRaises(IOError):
            host.get_file("not-a-file", "not-another-file", print_output=True)
