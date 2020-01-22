from subprocess import PIPE
from unittest import TestCase

from mock import MagicMock, mock_open, patch

from pyinfra.api import Config, State
from pyinfra.api.connect import connect_all
from pyinfra.api.util import make_command

from ..util import make_inventory


@patch('pyinfra.api.connectors.local.mkstemp', lambda: (None, '__tempfile__'))
@patch('pyinfra.api.connectors.local.os.remove', lambda f: None)
@patch('pyinfra.api.connectors.local.open', mock_open(read_data='test!'), create=True)
@patch('pyinfra.api.util.open', mock_open(read_data='test!'), create=True)
class TestLocalConnector(TestCase):
    def setUp(self):
        self.fake_popen_patch = patch('pyinfra.api.connectors.util.Popen')
        self.fake_popen_mock = self.fake_popen_patch.start()

    def tearDown(self):
        self.fake_popen_patch.stop()

    def test_connect_all(self):
        inventory = make_inventory(hosts=('@local',))
        state = State(inventory, Config())
        connect_all(state)
        self.assertEqual(len(state.active_hosts), 1)

    def test_connect_host(self):
        inventory = make_inventory(hosts=('@local',))
        state = State(inventory, Config())
        host = inventory.get_host('@local')
        host.connect(state, for_fact=True)
        self.assertEqual(len(state.active_hosts), 0)

    def test_run_shell_command(self):
        inventory = make_inventory(hosts=('@local',))
        state = State(inventory, Config())
        host = inventory.get_host('@local')

        command = 'echo hi'
        self.fake_popen_mock().returncode = 0

        out = host.run_shell_command(state, command, stdin='hello', print_output=True)
        assert len(out) == 3

        status, stdout, stderr = out
        assert status is True
        self.fake_popen_mock().stdin.write.assert_called_with(b'hello\n')

        combined_out = host.run_shell_command(
            state, command, stdin='hello', print_output=True,
            return_combined_output=True,
        )
        assert len(combined_out) == 2

        shell_command = make_command(command)
        self.fake_popen_mock.assert_called_with(
            shell_command, shell=True,
            stdout=PIPE, stderr=PIPE, stdin=PIPE,
        )

    def test_run_shell_command_success_exit_codes(self):
        inventory = make_inventory(hosts=('@local',))
        state = State(inventory, Config())
        host = inventory.get_host('@local')

        command = 'echo hi'
        self.fake_popen_mock().returncode = 1

        out = host.run_shell_command(state, command, success_exit_codes=[1])
        assert len(out) == 3
        assert out[0] is True

    def test_run_shell_command_error(self):
        inventory = make_inventory(hosts=('@local',))
        state = State(inventory, Config())
        host = inventory.get_host('@local')

        command = 'echo hi'
        self.fake_popen_mock().returncode = 1

        out = host.run_shell_command(state, command)
        assert len(out) == 3
        assert out[0] is False

    def test_put_file(self):
        inventory = make_inventory(hosts=('@local',))
        state = State(inventory, Config())

        host = inventory.get_host('@local')

        fake_process = MagicMock(returncode=0)
        self.fake_popen_mock.return_value = fake_process

        host.put_file(state, 'not-a-file', 'not-another-file', print_output=True)

        self.fake_popen_mock.assert_called_with(
            "sh -c 'cp __tempfile__ not-another-file'", shell=True,
            stdout=PIPE, stderr=PIPE, stdin=PIPE,
        )

    def test_put_file_error(self):
        inventory = make_inventory(hosts=('@local',))
        state = State(inventory, Config())

        host = inventory.get_host('@local')

        fake_process = MagicMock(returncode=1)
        self.fake_popen_mock.return_value = fake_process

        with self.assertRaises(IOError):
            host.put_file(state, 'not-a-file', 'not-another-file', print_output=True)

    def test_get_file(self):
        inventory = make_inventory(hosts=('@local',))
        state = State(inventory, Config())

        host = inventory.get_host('@local')

        fake_process = MagicMock(returncode=0)
        self.fake_popen_mock.return_value = fake_process

        host.get_file(state, 'not-a-file', 'not-another-file', print_output=True)

        self.fake_popen_mock.assert_called_with(
            "sh -c 'cp not-a-file __tempfile__'", shell=True,
            stdout=PIPE, stderr=PIPE, stdin=PIPE,
        )

    def test_get_file_error(self):
        inventory = make_inventory(hosts=('@local',))
        state = State(inventory, Config())

        host = inventory.get_host('@local')

        fake_process = MagicMock(returncode=1)
        self.fake_popen_mock.return_value = fake_process

        with self.assertRaises(IOError):
            host.get_file(state, 'not-a-file', 'not-another-file', print_output=True)
