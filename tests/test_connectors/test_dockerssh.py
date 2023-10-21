# encoding: utf-8

import shlex
from unittest import TestCase
from unittest.mock import MagicMock, mock_open, patch

from pyinfra.api import Config, State
from pyinfra.api.connect import connect_all
from pyinfra.api.exceptions import InventoryError, PyinfraError
from pyinfra.connectors.util import CommandOutput, OutputLine, make_unix_command

from ..util import make_inventory


def fake_ssh_docker_shell(
    self,
    command,
    print_output=False,
    print_input=False,
    **command_kwargs,
):
    if str(command) == "docker run -d not-an-image tail -f /dev/null":
        return (True, CommandOutput([OutputLine("stdout", "containerid")]))

    if str(command) == "docker commit containerid":
        return (True, CommandOutput([OutputLine("stdout", "sha256:blahsomerandomstringdata")]))

    if str(command) == "docker rm -f containerid":
        return (True, CommandOutput([]))

    if str(command).startswith("rm -f"):
        return (True, CommandOutput([]))

    if "$TMPDIR" in str(command):
        return (True, CommandOutput([]))

    # This is a bit messy. But it's easier than trying to swap out a mock
    # when it needs to be used...
    if fake_ssh_docker_shell.custom_command:
        custom_command, status, output = fake_ssh_docker_shell.custom_command
        if str(command) == custom_command:
            fake_ssh_docker_shell.ran_custom_command = True
            return (status, output)

    raise PyinfraError("Invalid Command: {0}".format(command))


def get_docker_command(command):
    shell_command = make_unix_command(command).get_raw_value()
    shell_command = shlex.quote(shell_command)
    docker_command = "docker exec -it containerid sh -c {0}".format(shell_command)
    return docker_command


@patch("pyinfra.connectors.ssh.SSHConnector.connect", MagicMock())
@patch("pyinfra.connectors.ssh.SSHConnector.run_shell_command", fake_ssh_docker_shell)
@patch("pyinfra.api.util.open", mock_open(read_data="test!"), create=True)
class TestDockerSSHConnector(TestCase):
    def setUp(self):
        # reset custom command for shell
        fake_ssh_docker_shell.custom_command = None
        fake_ssh_docker_shell.ran_custom_command = False

    def test_connect_host(self):
        inventory = make_inventory(("somehost", "anotherhost"))
        state = State(inventory, Config())
        host = inventory.get_host("somehost")
        host.connect(reason=True)
        assert len(state.active_hosts) == 0

    def test_missing_image_and_host(self):
        with self.assertRaises(InventoryError):
            make_inventory(hosts=("@dockerssh",))

    def test_missing_image(self):
        with self.assertRaises(InventoryError):
            make_inventory(hosts=("@dockerssh/host",))

        with self.assertRaises(InventoryError):
            make_inventory(hosts=("@dockerssh/host:",))

    def test_connect_all(self):
        inventory = make_inventory(hosts=("@dockerssh/somehost:not-an-image",))
        state = State(inventory, Config())
        connect_all(state)
        assert len(state.active_hosts) == 1

    def test_user_provided_container_id(self):
        inventory = make_inventory(
            hosts=(("@dockerssh/somehost:not-an-image", {"docker_container_id": "abc"}),),
        )
        State(inventory, Config())
        host = inventory.get_host("@dockerssh/somehost:not-an-image")
        host.connect()
        assert host.data.docker_container_id == "abc"

    def test_connect_all_error(self):
        inventory = make_inventory(hosts=("@dockerssh/somehost:a-broken-image",))
        state = State(inventory, Config())

        with self.assertRaises(PyinfraError):
            connect_all(state)

    def test_connect_disconnect_host(self):
        inventory = make_inventory(hosts=("@dockerssh/somehost:not-an-image",))
        state = State(inventory, Config())
        host = inventory.get_host("@dockerssh/somehost:not-an-image")
        host.connect(reason=True)
        assert len(state.active_hosts) == 0
        host.disconnect()

    def test_run_shell_command(self):
        inventory = make_inventory(hosts=("@dockerssh/somehost:not-an-image",))
        State(inventory, Config())

        command = "echo hi"

        fake_ssh_docker_shell.custom_command = [get_docker_command(command), True, []]

        host = inventory.get_host("@dockerssh/somehost:not-an-image")
        host.connect()
        out = host.run_shell_command(
            command,
            _stdin="hello",
            _get_pty=True,
            print_output=True,
        )
        assert len(out) == 2
        assert out[0] is True
        assert fake_ssh_docker_shell.ran_custom_command

    def test_run_shell_command_error(self):
        inventory = make_inventory(hosts=("@dockerssh/somehost:not-an-image",))
        state = State(inventory, Config())

        command = "echo hi"
        fake_ssh_docker_shell.custom_command = [get_docker_command(command), False, []]

        host = inventory.get_host("@dockerssh/somehost:not-an-image")
        host.connect(state)
        out = host.run_shell_command(command, _get_pty=True)
        assert out[0] is False
        assert fake_ssh_docker_shell.ran_custom_command

    @patch("pyinfra.connectors.dockerssh.mkstemp", lambda: (None, "local_tempfile"))
    @patch("pyinfra.connectors.docker.os.close", lambda f: None)
    @patch("pyinfra.connectors.ssh.SSHConnector.put_file")
    def test_put_file(self, fake_put_file):
        fake_ssh_docker_shell.custom_command = [
            "docker cp remote_tempfile containerid:not-another-file",
            True,
            [],
        ]

        inventory = make_inventory(hosts=("@dockerssh/somehost:not-an-image",))
        State(inventory, Config())

        host = inventory.get_host("@dockerssh/somehost:not-an-image")
        host.get_temp_filename = lambda _: "remote_tempfile"
        host.connect()

        host.put_file("not-a-file", "not-another-file", print_output=True)

        # ensure copy from local to remote host
        fake_put_file.assert_called_with("local_tempfile", "remote_tempfile")

        # ensure copy from remote host to remote docker container
        assert fake_ssh_docker_shell.ran_custom_command

    @patch("pyinfra.connectors.ssh.SSHConnector.put_file")
    def test_put_file_error(self, fake_put_file):
        inventory = make_inventory(hosts=("@dockerssh/somehost:not-an-image",))
        State(inventory, Config())

        host = inventory.get_host("@dockerssh/somehost:not-an-image")
        host.get_temp_filename = lambda _: "remote_tempfile"
        host.connect()

        # SSH error
        fake_put_file.return_value = False
        with self.assertRaises(IOError):
            host.put_file("not-a-file", "not-another-file", print_output=True)

        # docker copy error
        fake_ssh_docker_shell.custom_command = [
            "docker cp remote_tempfile containerid:not-another-file",
            False,
            CommandOutput([OutputLine("stderr", "docker error")]),
        ]
        fake_put_file.return_value = True

        with self.assertRaises(IOError) as e:
            host.put_file("not-a-file", "not-another-file", print_output=True)
        assert str(e.exception) == "docker error"

    @patch("pyinfra.connectors.ssh.SSHConnector.get_file")
    def test_get_file(self, fake_get_file):
        fake_ssh_docker_shell.custom_command = [
            "docker cp containerid:not-a-file remote_tempfile",
            True,
            [],
        ]

        inventory = make_inventory(hosts=("@dockerssh/somehost:not-an-image",))
        State(inventory, Config())

        host = inventory.get_host("@dockerssh/somehost:not-an-image")
        host.get_temp_filename = lambda _: "remote_tempfile"
        host.connect()

        host.get_file("not-a-file", "not-another-file", print_output=True)

        # ensure copy from local to remote host
        fake_get_file.assert_called_with("remote_tempfile", "not-another-file")

        # ensure copy from remote host to remote docker container
        assert fake_ssh_docker_shell.ran_custom_command

    @patch("pyinfra.connectors.ssh.SSHConnector.get_file")
    def test_get_file_error(self, fake_get_file):
        fake_ssh_docker_shell.custom_command = [
            "docker cp containerid:not-a-file remote_tempfile",
            False,
            CommandOutput([OutputLine("stderr", "docker error")]),
        ]

        inventory = make_inventory(hosts=("@dockerssh/somehost:not-an-image",))
        State(inventory, Config())

        host = inventory.get_host("@dockerssh/somehost:not-an-image")
        host.get_temp_filename = lambda _: "remote_tempfile"
        host.connect()

        fake_get_file.return_value = True
        with self.assertRaises(IOError) as ex:
            host.get_file("not-a-file", "not-another-file", print_output=True)

        assert str(ex.exception) == "docker error"

        # SSH error
        fake_ssh_docker_shell.custom_command = [
            "docker cp containerid:not-a-file remote_tempfile",
            True,
            [],
        ]
        fake_get_file.return_value = False
        with self.assertRaises(IOError) as ex:
            host.get_file("not-a-file", "not-another-file", print_output=True)

        assert str(ex.exception) == "failed to copy file over ssh"
