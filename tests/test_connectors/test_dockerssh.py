# encoding: utf-8

from __future__ import unicode_literals

from unittest import TestCase

from mock import MagicMock, mock_open, patch
from six.moves import shlex_quote

from pyinfra.api import Config, State
from pyinfra.api.connect import connect_all
from pyinfra.api.connectors.util import make_unix_command
from pyinfra.api.exceptions import InventoryError, PyinfraError

from ..util import make_inventory


def fake_ssh_docker_shell(state, host, command,
                          get_pty=False,
                          timeout=None,
                          stdin=None,
                          success_exit_codes=None,
                          print_output=False,
                          print_input=False,
                          return_combined_output=False,
                          use_sudo_password=False,
                          **command_kwargs
                          ):
    if host.data.ssh_hostname not in ('somehost', 'anotherhost'):
        raise PyinfraError('Invalid host', host.data.ssh_hostname)

    if command == 'docker run -d not-an-image tail -f /dev/null':
        return (True, ['containerid'], [])

    elif command == 'docker commit containerid':
        return (True, ['sha256:blahsomerandomstringdata'], [])

    elif command == 'docker rm -f containerid':
        return (True, [], [])

    elif str(command).startswith('rm -f'):
        return (True, [], [])

    # This is a bit kludgy. But it's easier than trying to swap out a mock
    # when it needs to be used...
    elif fake_ssh_docker_shell.custom_command:
        custom_command, status, stdout, stderr = fake_ssh_docker_shell.custom_command
        if str(command) == custom_command:
            fake_ssh_docker_shell.ran_custom_command = True
            return (status, stdout, stderr)

    raise PyinfraError('Invalid Command: {0}'.format(command))


def get_docker_command(command):
    shell_command = make_unix_command(command).get_raw_value()
    shell_command = shlex_quote(shell_command)
    docker_command = 'docker exec -it containerid sh -c {0}'.format(shell_command)
    return docker_command


@patch('pyinfra.api.connectors.ssh.connect', MagicMock())
@patch('pyinfra.api.connectors.ssh.run_shell_command', fake_ssh_docker_shell)
@patch('pyinfra.api.util.open', mock_open(read_data='test!'), create=True)
class TestDockerSSHConnector(TestCase):
    def setUp(self):
        # reset custom command for shell
        fake_ssh_docker_shell.custom_command = None
        fake_ssh_docker_shell.ran_custom_command = False

    def test_connect_host(self):
        inventory = make_inventory(('somehost', 'anotherhost'))
        state = State(inventory, Config())
        host = inventory.get_host('somehost')
        host.connect(reason=True)
        assert len(state.active_hosts) == 0

    def test_missing_image_and_host(self):
        with self.assertRaises(InventoryError):
            make_inventory(hosts=('@dockerssh',))

    def test_missing_image(self):
        with self.assertRaises(InventoryError):
            make_inventory(hosts=('@dockerssh/host',))

        with self.assertRaises(InventoryError):
            make_inventory(hosts=('@dockerssh/host:',))

    def test_connect_all(self):
        inventory = make_inventory(hosts=('@dockerssh/somehost:not-an-image',))
        state = State(inventory, Config())
        connect_all(state)
        assert len(state.active_hosts) == 1

    def test_user_provided_container_id(self):
        inventory = make_inventory(hosts=(
            ('@dockerssh/somehost:not-an-image', {'docker_container_id': 'abc'}),
        ))
        State(inventory, Config())
        host = inventory.get_host('@dockerssh/somehost:not-an-image')
        host.connect()
        assert host.data.docker_container_id == 'abc'

    def test_connect_all_error(self):
        inventory = make_inventory(hosts=('@dockerssh/somehost:a-broken-image',))
        state = State(inventory, Config())

        with self.assertRaises(PyinfraError):
            connect_all(state)

    def test_connect_disconnect_host(self):
        inventory = make_inventory(hosts=('@dockerssh/somehost:not-an-image',))
        state = State(inventory, Config())
        host = inventory.get_host('@dockerssh/somehost:not-an-image')
        host.connect(reason=True)
        assert len(state.active_hosts) == 0
        host.disconnect()

    def test_run_shell_command(self):
        inventory = make_inventory(hosts=('@dockerssh/somehost:not-an-image',))
        State(inventory, Config())

        command = 'echo hi'

        fake_ssh_docker_shell.custom_command = [get_docker_command(command), True, [], []]

        host = inventory.get_host('@dockerssh/somehost:not-an-image')
        host.connect()
        out = host.run_shell_command(
            command,
            stdin='hello',
            get_pty=True,
            print_output=True,
        )
        assert len(out) == 3
        assert out[0] is True
        assert fake_ssh_docker_shell.ran_custom_command

    def test_run_shell_command_error(self):
        inventory = make_inventory(hosts=('@dockerssh/somehost:not-an-image',))
        state = State(inventory, Config())

        command = 'echo hi'
        fake_ssh_docker_shell.custom_command = [get_docker_command(command), False, [], []]

        host = inventory.get_host('@dockerssh/somehost:not-an-image')
        host.connect(state)
        out = host.run_shell_command(command, get_pty=True)
        assert out[0] is False
        assert fake_ssh_docker_shell.ran_custom_command

    @patch('pyinfra.api.connectors.dockerssh.mkstemp', lambda: (None, 'local_tempfile'))
    @patch('pyinfra.api.connectors.docker.os.close', lambda f: None)
    @patch('pyinfra.api.connectors.dockerssh.ssh.put_file')
    def test_put_file(self, fake_put_file):
        fake_ssh_docker_shell.custom_command = [
            'docker cp remote_tempfile containerid:not-another-file', True, [], []]

        inventory = make_inventory(hosts=('@dockerssh/somehost:not-an-image',))
        state = State(inventory, Config())
        state.get_temp_filename = lambda _: 'remote_tempfile'

        host = inventory.get_host('@dockerssh/somehost:not-an-image')
        host.connect()

        host.put_file('not-a-file', 'not-another-file', print_output=True)

        # ensure copy from local to remote host
        fake_put_file.assert_called_with(state, host, 'local_tempfile', 'remote_tempfile')

        # ensure copy from remote host to remote docker container
        assert fake_ssh_docker_shell.ran_custom_command

    @patch('pyinfra.api.connectors.dockerssh.ssh.put_file')
    def test_put_file_error(self, fake_put_file):
        inventory = make_inventory(hosts=('@dockerssh/somehost:not-an-image',))
        state = State(inventory, Config())
        state.get_temp_filename = lambda _: 'remote_tempfile'

        host = inventory.get_host('@dockerssh/somehost:not-an-image')
        host.connect()

        # SSH error
        fake_put_file.return_value = False
        with self.assertRaises(IOError):
            host.put_file('not-a-file', 'not-another-file', print_output=True)

        # docker copy error
        fake_ssh_docker_shell.custom_command = [
            'docker cp remote_tempfile containerid:not-another-file',
            False, [], ['docker error']]
        fake_put_file.return_value = True

        with self.assertRaises(IOError) as exn:
            host.put_file('not-a-file', 'not-another-file', print_output=True)
        assert str(exn.exception) == 'docker error'

    @patch('pyinfra.api.connectors.dockerssh.ssh.get_file')
    def test_get_file(self, fake_get_file):
        fake_ssh_docker_shell.custom_command = [
            'docker cp containerid:not-a-file remote_tempfile', True, [], []]

        inventory = make_inventory(hosts=('@dockerssh/somehost:not-an-image',))
        state = State(inventory, Config())
        state.get_temp_filename = lambda _: 'remote_tempfile'

        host = inventory.get_host('@dockerssh/somehost:not-an-image')
        host.connect()

        host.get_file('not-a-file', 'not-another-file', print_output=True)

        # ensure copy from local to remote host
        fake_get_file.assert_called_with(state, host, 'remote_tempfile', 'not-another-file')

        # ensure copy from remote host to remote docker container
        assert fake_ssh_docker_shell.ran_custom_command

    @patch('pyinfra.api.connectors.dockerssh.ssh.get_file')
    def test_get_file_error(self, fake_get_file):
        fake_ssh_docker_shell.custom_command = [
            'docker cp containerid:not-a-file remote_tempfile', False, [], ['docker error']]

        inventory = make_inventory(hosts=('@dockerssh/somehost:not-an-image',))
        state = State(inventory, Config())
        state.get_temp_filename = lambda _: 'remote_tempfile'

        host = inventory.get_host('@dockerssh/somehost:not-an-image')
        host.connect()

        fake_get_file.return_value = True
        with self.assertRaises(IOError) as ex:
            host.get_file('not-a-file', 'not-another-file', print_output=True)

        assert str(ex.exception) == 'docker error'

        # SSH error
        fake_ssh_docker_shell.custom_command = [
            'docker cp containerid:not-a-file remote_tempfile', True, [], []]
        fake_get_file.return_value = False
        with self.assertRaises(IOError) as ex:
            host.get_file('not-a-file', 'not-another-file', print_output=True)

        assert str(ex.exception) == 'failed to copy file over ssh'
