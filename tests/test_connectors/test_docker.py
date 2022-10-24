import shlex
from subprocess import PIPE
from unittest import TestCase
from unittest.mock import MagicMock, mock_open, patch

from pyinfra.api import Config, State
from pyinfra.api.connect import connect_all
from pyinfra.api.exceptions import InventoryError, PyinfraError
from pyinfra.connectors.util import make_unix_command

from ..util import make_inventory


def fake_docker_shell(command, splitlines=None):
    if command == "docker run -d not-an-image tail -f /dev/null":
        return ["containerid"]

    if command == "docker commit containerid":
        return ["sha256:blahsomerandomstringdata"]

    if command == "docker rm -f containerid":
        return []

    raise PyinfraError("Invalid command: {0}".format(command))


@patch("pyinfra.connectors.docker.local.shell", fake_docker_shell)
@patch("pyinfra.connectors.docker.mkstemp", lambda: (None, "__tempfile__"))
@patch("pyinfra.connectors.docker.os.remove", lambda f: None)
@patch("pyinfra.connectors.docker.os.close", lambda f: None)
@patch("pyinfra.connectors.docker.open", mock_open(read_data="test!"), create=True)
@patch("pyinfra.api.util.open", mock_open(read_data="test!"), create=True)
class TestDockerConnector(TestCase):
    def setUp(self):
        self.fake_popen_patch = patch("pyinfra.connectors.util.Popen")
        self.fake_popen_mock = self.fake_popen_patch.start()

    def tearDown(self):
        self.fake_popen_patch.stop()

    def test_missing_image(self):
        with self.assertRaises(InventoryError):
            make_inventory(hosts=("@docker",))

    def test_user_provided_container_id(self):
        inventory = make_inventory(
            hosts=(("@docker/not-an-image", {"docker_container_id": "abc"}),),
        )
        State(inventory, Config())
        host = inventory.get_host("@docker/not-an-image")
        host.connect()
        assert host.data.docker_container_id == "abc"

    def test_connect_all(self):
        inventory = make_inventory(hosts=("@docker/not-an-image",))
        state = State(inventory, Config())
        connect_all(state)
        assert len(state.active_hosts) == 1

    def test_connect_all_error(self):
        inventory = make_inventory(hosts=("@docker/a-broken-image",))
        state = State(inventory, Config())

        with self.assertRaises(PyinfraError):
            connect_all(state)

    def test_connect_disconnect_host(self):
        inventory = make_inventory(hosts=("@docker/not-an-image",))
        state = State(inventory, Config())
        host = inventory.get_host("@docker/not-an-image")
        host.connect(reason=True)
        assert len(state.active_hosts) == 0
        host.disconnect()

    def test_run_shell_command(self):
        inventory = make_inventory(hosts=("@docker/not-an-image",))
        State(inventory, Config())

        command = "echo hi"
        self.fake_popen_mock().returncode = 0

        host = inventory.get_host("@docker/not-an-image")
        host.connect()
        out = host.run_shell_command(
            command,
            stdin="hello",
            get_pty=True,
            print_output=True,
        )
        assert len(out) == 3
        assert out[0] is True

        command = make_unix_command(command).get_raw_value()
        command = shlex.quote(command)
        docker_command = "docker exec -it containerid sh -c {0}".format(command)
        shell_command = make_unix_command(docker_command).get_raw_value()

        self.fake_popen_mock.assert_called_with(
            shell_command,
            shell=True,
            stdout=PIPE,
            stderr=PIPE,
            stdin=PIPE,
        )

    def test_run_shell_command_success_exit_codes(self):
        inventory = make_inventory(hosts=("@docker/not-an-image",))
        State(inventory, Config())

        command = "echo hi"
        self.fake_popen_mock().returncode = 1

        host = inventory.get_host("@docker/not-an-image")
        host.connect()
        out = host.run_shell_command(command, success_exit_codes=[1])
        assert out[0] is True

    def test_run_shell_command_error(self):
        inventory = make_inventory(hosts=("@docker/not-an-image",))
        state = State(inventory, Config())

        command = "echo hi"
        self.fake_popen_mock().returncode = 1

        host = inventory.get_host("@docker/not-an-image")
        host.connect(state)
        out = host.run_shell_command(command)
        assert out[0] is False

    def test_put_file(self):
        inventory = make_inventory(hosts=("@docker/not-an-image",))
        State(inventory, Config())

        host = inventory.get_host("@docker/not-an-image")
        host.connect()

        fake_process = MagicMock(returncode=0)
        self.fake_popen_mock.return_value = fake_process

        host.put_file("not-a-file", "not-another-file", print_output=True)

        self.fake_popen_mock.assert_called_with(
            "sh -c 'docker cp __tempfile__ containerid:not-another-file'",
            shell=True,
            stdout=PIPE,
            stderr=PIPE,
            stdin=PIPE,
        )

    def test_put_file_error(self):
        inventory = make_inventory(hosts=("@docker/not-an-image",))
        State(inventory, Config())

        host = inventory.get_host("@docker/not-an-image")
        host.connect()

        fake_process = MagicMock(returncode=1)
        self.fake_popen_mock.return_value = fake_process

        with self.assertRaises(IOError):
            host.put_file("not-a-file", "not-another-file", print_output=True)

    def test_get_file(self):
        inventory = make_inventory(hosts=("@docker/not-an-image",))
        State(inventory, Config())

        host = inventory.get_host("@docker/not-an-image")
        host.connect()

        fake_process = MagicMock(returncode=0)
        self.fake_popen_mock.return_value = fake_process

        host.get_file("not-a-file", "not-another-file", print_output=True)

        self.fake_popen_mock.assert_called_with(
            "sh -c 'docker cp containerid:not-a-file __tempfile__'",
            shell=True,
            stdout=PIPE,
            stderr=PIPE,
            stdin=PIPE,
        )

    def test_get_file_error(self):
        inventory = make_inventory(hosts=("@docker/not-an-image",))
        State(inventory, Config())

        host = inventory.get_host("@docker/not-an-image")
        host.connect()

        fake_process = MagicMock(returncode=1)
        self.fake_popen_mock.return_value = fake_process

        with self.assertRaises(IOError):
            host.get_file("not-a-file", "not-another-file", print_output=True)
