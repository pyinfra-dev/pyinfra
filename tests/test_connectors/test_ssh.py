# encoding: utf-8

from __future__ import unicode_literals

from socket import (
    error as socket_error,
    gaierror,
)
from unittest import TestCase

from mock import call, MagicMock, mock_open, patch
from paramiko import (
    AuthenticationException,
    PasswordRequiredException,
    SSHException,
)

import pyinfra

from pyinfra.api import Config, MaskString, State, StringCommand
from pyinfra.api.connect import connect_all
from pyinfra.api.connectors.ssh import _get_sftp_connection
from pyinfra.api.exceptions import ConnectError, PyinfraError

from ..util import make_inventory


@patch('pyinfra.api.connectors.ssh.SSHClient.get_transport', MagicMock())
@patch('pyinfra.api.connectors.ssh.open', mock_open(read_data='test!'), create=True)
class TestSSHConnector(TestCase):
    def setUp(self):
        self.fake_connect_patch = patch('pyinfra.api.connectors.ssh.SSHClient.connect')
        self.fake_connect_mock = self.fake_connect_patch.start()
        _get_sftp_connection.cache = {}

    def tearDown(self):
        self.fake_connect_patch.stop()

    def test_connect_all(self):
        inventory = make_inventory()
        state = State(inventory, Config())
        connect_all(state)
        assert len(state.active_hosts) == 2

    def test_connect_host(self):
        inventory = make_inventory()
        state = State(inventory, Config())
        host = inventory.get_host('somehost')
        host.connect(reason=True)
        assert len(state.active_hosts) == 0

    def test_connect_all_password(self):
        inventory = make_inventory(ssh_password='test')

        # Get a host
        somehost = inventory.get_host('somehost')
        assert somehost.data.ssh_password == 'test'

        state = State(inventory, Config())
        connect_all(state)

        assert len(state.active_hosts) == 2

    @patch('pyinfra.api.connectors.ssh.path.isfile', lambda *args, **kwargs: True)
    @patch('pyinfra.api.connectors.ssh.RSAKey.from_private_key_file')
    def test_connect_exceptions(self, fake_key_open):
        for exception_class in (
            AuthenticationException,
            SSHException,
            gaierror,
            socket_error,
            EOFError,
        ):
            state = State(make_inventory(hosts=(
                ('somehost', {'ssh_key': 'testkey'}),
            )), Config())

            def raise_exception(*args, **kwargs):
                raise exception_class

            self.fake_connect_mock.side_effect = raise_exception

            with self.assertRaises(PyinfraError):
                connect_all(state)

            assert len(state.active_hosts) == 0

    def test_connect_with_rsa_ssh_key(self):
        state = State(make_inventory(hosts=(
            ('somehost', {'ssh_key': 'testkey'}),
        )), Config())

        with patch('pyinfra.api.connectors.ssh.path.isfile', lambda *args, **kwargs: True), \
                patch('pyinfra.api.connectors.ssh.RSAKey.from_private_key_file') as fake_key_open:

            fake_key = MagicMock()
            fake_key_open.return_value = fake_key

            state.deploy_dir = '/'

            connect_all(state)

            # Check the key was created properly
            fake_key_open.assert_called_with(filename='testkey')
            # Check the certificate file was then loaded
            fake_key.load_certificate.assert_called_with('testkey.pub')

            # And check the Paramiko SSH call was correct
            self.fake_connect_mock.assert_called_with(
                'somehost',
                allow_agent=False,
                look_for_keys=False,
                pkey=fake_key,
                timeout=10,
                username='vagrant',
            )

        # Check that loading the same key again is cached in the state
        second_state = State(make_inventory(hosts=(
            ('somehost', {'ssh_key': 'testkey'}),
        )), Config())
        second_state.private_keys = state.private_keys

        connect_all(second_state)

    def test_connect_with_rsa_ssh_key_password(self):
        state = State(make_inventory(hosts=(
            ('somehost', {'ssh_key': 'testkey', 'ssh_key_password': 'testpass'}),
        )), Config())

        with patch(
            'pyinfra.api.connectors.ssh.path.isfile',
            lambda *args, **kwargs: True,
        ), patch(
            'pyinfra.api.connectors.ssh.RSAKey.from_private_key_file',
        ) as fake_key_open:
            fake_key = MagicMock()

            def fake_key_open_fail(*args, **kwargs):
                if 'password' not in kwargs:
                    raise PasswordRequiredException()
                return fake_key

            fake_key_open.side_effect = fake_key_open_fail

            state.deploy_dir = '/'

            connect_all(state)

            # Check the key was created properly
            fake_key_open.assert_called_with(filename='testkey', password='testpass')
            # Check the certificate file was then loaded
            fake_key.load_certificate.assert_called_with('testkey.pub')

    def test_connect_with_rsa_ssh_key_password_from_prompt(self):
        state = State(make_inventory(hosts=(
            ('somehost', {'ssh_key': 'testkey'}),
        )), Config())

        with patch(
            'pyinfra.api.connectors.ssh.path.isfile',
            lambda *args, **kwargs: True,
        ), patch(
            'pyinfra.api.connectors.ssh.getpass',
            lambda *args, **kwargs: 'testpass',
        ), patch(
            'pyinfra.api.connectors.ssh.RSAKey.from_private_key_file',
        ) as fake_key_open:
            fake_key = MagicMock()

            def fake_key_open_fail(*args, **kwargs):
                if 'password' not in kwargs:
                    raise PasswordRequiredException()
                return fake_key

            fake_key_open.side_effect = fake_key_open_fail

            state.deploy_dir = '/'

            pyinfra.is_cli = True
            connect_all(state)
            pyinfra.is_cli = False

            # Check the key was created properly
            fake_key_open.assert_called_with(filename='testkey', password='testpass')
            # Check the certificate file was then loaded
            fake_key.load_certificate.assert_called_with('testkey.pub')

    def test_connect_with_rsa_ssh_key_missing_password(self):
        state = State(make_inventory(hosts=(
            ('somehost', {'ssh_key': 'testkey'}),
        )), Config())

        with patch(
            'pyinfra.api.connectors.ssh.path.isfile',
            lambda *args, **kwargs: True,
        ), patch(
            'pyinfra.api.connectors.ssh.RSAKey.from_private_key_file',
        ) as fake_key_open:

            def fake_key_open_fail(*args, **kwargs):
                raise PasswordRequiredException

            fake_key_open.side_effect = fake_key_open_fail

            fake_key = MagicMock()
            fake_key_open.return_value = fake_key

            state.deploy_dir = '/'

            with self.assertRaises(PyinfraError) as e:
                connect_all(state)

            assert e.exception.args[0] == (
                'Private key file (testkey) is encrypted, set ssh_key_password '
                'to use this key'
            )

    def test_connect_with_rsa_ssh_key_wrong_password(self):
        state = State(make_inventory(hosts=(
            ('somehost', {'ssh_key': 'testkey', 'ssh_key_password': 'testpass'}),
        )), Config())

        with patch(
            'pyinfra.api.connectors.ssh.path.isfile',
            lambda *args, **kwargs: True,
        ), patch(
            'pyinfra.api.connectors.ssh.RSAKey.from_private_key_file',
        ) as fake_key_open:

            def fake_key_open_fail(*args, **kwargs):
                if 'password' not in kwargs:
                    raise PasswordRequiredException
                raise SSHException

            fake_key_open.side_effect = fake_key_open_fail

            fake_key = MagicMock()
            fake_key_open.return_value = fake_key

            state.deploy_dir = '/'

            with self.assertRaises(PyinfraError) as e:
                connect_all(state)

            assert e.exception.args[0] == 'Incorrect password for private key: testkey'

    def test_connect_with_dss_ssh_key(self):
        state = State(make_inventory(hosts=(
            ('somehost', {'ssh_key': 'testkey'}),
        )), Config())

        with patch('pyinfra.api.connectors.ssh.path.isfile', lambda *args, **kwargs: True), \
                patch('pyinfra.api.connectors.ssh.RSAKey.from_private_key_file') as fake_rsa_key_open, \
                patch('pyinfra.api.connectors.ssh.DSSKey.from_private_key_file') as fake_key_open:  # noqa

            def fake_rsa_key_open_fail(*args, **kwargs):
                raise SSHException

            fake_rsa_key_open.side_effect = fake_rsa_key_open_fail

            fake_key = MagicMock()
            fake_key_open.return_value = fake_key

            state.deploy_dir = '/'

            connect_all(state)

            # Check the key was created properly
            fake_key_open.assert_called_with(filename='testkey')

            # And check the Paramiko SSH call was correct
            self.fake_connect_mock.assert_called_with(
                'somehost',
                allow_agent=False,
                look_for_keys=False,
                pkey=fake_key,
                timeout=10,
                username='vagrant',
            )

        # Check that loading the same key again is cached in the state
        second_state = State(make_inventory(hosts=(
            ('somehost', {'ssh_key': 'testkey'}),
        )), Config())
        second_state.private_keys = state.private_keys

        connect_all(second_state)

    def test_connect_with_missing_ssh_key(self):
        state = State(make_inventory(hosts=(
            ('somehost', {'ssh_key': 'testkey'}),
        )), Config())

        with self.assertRaises(PyinfraError) as e:
            connect_all(state)

        self.assertTrue(e.exception.args[0].startswith('No such private key file:'))

    @patch('pyinfra.api.connectors.ssh.SSHClient')
    def test_run_shell_command(self, fake_ssh_client):
        fake_ssh = MagicMock()
        fake_stdin = MagicMock()
        fake_stdout = MagicMock()
        fake_ssh.exec_command.return_value = fake_stdin, fake_stdout, MagicMock()

        fake_ssh_client.return_value = fake_ssh

        inventory = make_inventory(hosts=('somehost',))
        State(inventory, Config())
        host = inventory.get_host('somehost')
        host.connect()

        command = 'echo Šablony'
        fake_stdout.channel.recv_exit_status.return_value = 0

        out = host.run_shell_command(command, stdin='hello', print_output=True)
        assert len(out) == 3

        status, stdout, stderr = out
        assert status is True
        fake_stdin.write.assert_called_with(b'hello\n')

        combined_out = host.run_shell_command(
            command, stdin='hello', print_output=True,
            return_combined_output=True,
        )
        assert len(combined_out) == 2

        fake_ssh.exec_command.assert_called_with("sh -c 'echo Šablony'", get_pty=False)

    @patch('pyinfra.api.connectors.ssh.click')
    @patch('pyinfra.api.connectors.ssh.SSHClient')
    def test_run_shell_command_masked(self, fake_ssh_client, fake_click):
        fake_ssh = MagicMock()
        fake_stdout = MagicMock()
        fake_ssh.exec_command.return_value = MagicMock(), fake_stdout, MagicMock()

        fake_ssh_client.return_value = fake_ssh

        inventory = make_inventory(hosts=('somehost',))
        State(inventory, Config())
        host = inventory.get_host('somehost')
        host.connect()

        command = StringCommand('echo', MaskString('top-secret-stuff'))
        fake_stdout.channel.recv_exit_status.return_value = 0

        out = host.run_shell_command(command, print_output=True, print_input=True)
        assert len(out) == 3

        status, stdout, stderr = out
        assert status is True

        fake_ssh.exec_command.assert_called_with(
            "sh -c 'echo top-secret-stuff'",
            get_pty=False,
        )

        fake_click.echo.assert_called_with(
            "{0}>>> sh -c 'echo ***'".format(host.print_prefix),
            err=True,
        )

    @patch('pyinfra.api.connectors.ssh.SSHClient')
    def test_run_shell_command_success_exit_code(self, fake_ssh_client):
        fake_ssh = MagicMock()
        fake_stdin = MagicMock()
        fake_stdout = MagicMock()
        fake_ssh.exec_command.return_value = fake_stdin, fake_stdout, MagicMock()

        fake_ssh_client.return_value = fake_ssh

        inventory = make_inventory(hosts=('somehost',))
        State(inventory, Config())
        host = inventory.get_host('somehost')
        host.connect()

        command = 'echo hi'
        fake_stdout.channel.recv_exit_status.return_value = 1

        out = host.run_shell_command(command, success_exit_codes=[1])
        assert len(out) == 3
        assert out[0] is True

    @patch('pyinfra.api.connectors.ssh.SSHClient')
    def test_run_shell_command_error(self, fake_ssh_client):
        fake_ssh = MagicMock()
        fake_stdin = MagicMock()
        fake_stdout = MagicMock()
        fake_ssh.exec_command.return_value = fake_stdin, fake_stdout, MagicMock()

        fake_ssh_client.return_value = fake_ssh

        inventory = make_inventory(hosts=('somehost',))
        state = State(inventory, Config())
        host = inventory.get_host('somehost')
        host.connect(state)

        command = 'echo hi'
        fake_stdout.channel.recv_exit_status.return_value = 1

        out = host.run_shell_command(command)
        assert len(out) == 3
        assert out[0] is False

    @patch('pyinfra.api.connectors.ssh.SSHClient')
    @patch('pyinfra.api.connectors.ssh.SFTPClient')
    def test_put_file(self, fake_sftp_client, fake_ssh_client):
        inventory = make_inventory(hosts=('anotherhost',))
        State(inventory, Config())
        host = inventory.get_host('anotherhost')
        host.connect()

        fake_open = mock_open(read_data='test!')
        with patch('pyinfra.api.util.open', fake_open, create=True):
            status = host.put_file(
                'not-a-file', 'not-another-file',
                print_output=True,
            )

        assert status is True
        fake_sftp_client.from_transport().putfo.assert_called_with(
            fake_open(), 'not-another-file',
        )

    @patch('pyinfra.api.connectors.ssh.SSHClient')
    @patch('pyinfra.api.connectors.ssh.SFTPClient')
    def test_put_file_sudo(self, fake_sftp_client, fake_ssh_client):
        inventory = make_inventory(hosts=('anotherhost',))
        State(inventory, Config())
        host = inventory.get_host('anotherhost')
        host.connect()

        stdout_mock = MagicMock()
        stdout_mock.channel.recv_exit_status.return_value = 0
        fake_ssh_client().exec_command.return_value = MagicMock(), stdout_mock, MagicMock()

        fake_open = mock_open(read_data='test!')
        with patch('pyinfra.api.util.open', fake_open, create=True):
            status = host.put_file(
                'not-a-file', 'not-another-file',
                print_output=True,
                sudo=True,
                sudo_user='ubuntu',
            )

        assert status is True

        fake_ssh_client().exec_command.assert_called_with((
            "sudo -H -n -u ubuntu sh -c 'mv "
            '/tmp/pyinfra-43db9984686317089fefcf2e38de527e4cb44487 '
            "not-another-file && chown ubuntu not-another-file'"
        ), get_pty=False)

        fake_sftp_client.from_transport().putfo.assert_called_with(
            fake_open(), '/tmp/pyinfra-43db9984686317089fefcf2e38de527e4cb44487',
        )

    @patch('pyinfra.api.connectors.ssh.SSHClient')
    @patch('pyinfra.api.connectors.ssh.SFTPClient')
    def test_put_file_su_user_fail(self, fake_sftp_client, fake_ssh_client):
        inventory = make_inventory(hosts=('anotherhost',))
        State(inventory, Config())
        host = inventory.get_host('anotherhost')
        host.connect()

        stdout_mock = MagicMock()
        stdout_mock.channel.recv_exit_status.return_value = 1
        fake_ssh_client().exec_command.return_value = MagicMock(), stdout_mock, MagicMock()

        fake_open = mock_open(read_data='test!')
        with patch('pyinfra.api.util.open', fake_open, create=True):
            status = host.put_file(
                'not-a-file', 'not-another-file',
                print_output=True,
                su_user='centos',
            )

        assert status is False

        fake_ssh_client().exec_command.assert_called_with((
            "su centos -c 'sh -c '\"'\"'mv "
            '/tmp/pyinfra-43db9984686317089fefcf2e38de527e4cb44487 '
            "not-another-file && chown centos not-another-file'\"'\"''"
        ), get_pty=False)

        fake_sftp_client.from_transport().putfo.assert_called_with(
            fake_open(), '/tmp/pyinfra-43db9984686317089fefcf2e38de527e4cb44487',
        )

    @patch('pyinfra.api.connectors.ssh.SSHClient')
    @patch('pyinfra.api.connectors.ssh.SFTPClient')
    def test_get_file(self, fake_sftp_client, fake_ssh_client):
        inventory = make_inventory(hosts=('somehost',))
        State(inventory, Config())
        host = inventory.get_host('somehost')
        host.connect()

        fake_open = mock_open(read_data='test!')
        with patch('pyinfra.api.util.open', fake_open, create=True):
            status = host.get_file(
                'not-a-file', 'not-another-file',
                print_output=True,
            )

        assert status is True
        fake_sftp_client.from_transport().getfo.assert_called_with(
            'not-a-file', fake_open(),
        )

    @patch('pyinfra.api.connectors.ssh.SSHClient')
    @patch('pyinfra.api.connectors.ssh.SFTPClient')
    def test_get_file_sudo(self, fake_sftp_client, fake_ssh_client):
        inventory = make_inventory(hosts=('somehost',))
        State(inventory, Config())
        host = inventory.get_host('somehost')
        host.connect()

        stdout_mock = MagicMock()
        stdout_mock.channel.recv_exit_status.return_value = 0
        fake_ssh_client().exec_command.return_value = MagicMock(), stdout_mock, MagicMock()

        fake_open = mock_open(read_data='test!')
        with patch('pyinfra.api.util.open', fake_open, create=True):
            status = host.get_file(
                'not-a-file', 'not-another-file',
                print_output=True,
                sudo=True,
                sudo_user='ubuntu',
            )

        assert status is True

        fake_ssh_client().exec_command.assert_has_calls([
            call((
                "sudo -H -n -u ubuntu sh -c 'cp not-a-file "
                "/tmp/pyinfra-e9c0d3c8ffca943daa0e75511b0a09c84b59c508 && chmod +r not-a-file'"
            ), get_pty=False),
            call((
                "sudo -H -n -u ubuntu sh -c 'rm -f "
                "/tmp/pyinfra-e9c0d3c8ffca943daa0e75511b0a09c84b59c508'"
            ), get_pty=False),
        ])

        fake_sftp_client.from_transport().getfo.assert_called_with(
            '/tmp/pyinfra-e9c0d3c8ffca943daa0e75511b0a09c84b59c508', fake_open(),
        )

    @patch('pyinfra.api.connectors.ssh.SSHClient')
    def test_get_file_sudo_copy_fail(self, fake_ssh_client):
        inventory = make_inventory(hosts=('somehost',))
        State(inventory, Config())
        host = inventory.get_host('somehost')
        host.connect()

        stdout_mock = MagicMock()
        stdout_mock.channel.recv_exit_status.return_value = 1
        fake_ssh_client().exec_command.return_value = MagicMock(), stdout_mock, MagicMock()

        status = host.get_file(
            'not-a-file', 'not-another-file',
            print_output=True,
            sudo=True,
            sudo_user='ubuntu',
        )

        assert status is False

        fake_ssh_client().exec_command.assert_has_calls([
            call((
                "sudo -H -n -u ubuntu sh -c 'cp not-a-file "
                "/tmp/pyinfra-e9c0d3c8ffca943daa0e75511b0a09c84b59c508 && chmod +r not-a-file'"
            ), get_pty=False),
        ])

    @patch('pyinfra.api.connectors.ssh.SSHClient')
    @patch('pyinfra.api.connectors.ssh.SFTPClient')
    def test_get_file_sudo_remove_fail(self, fake_sftp_client, fake_ssh_client):
        inventory = make_inventory(hosts=('somehost',))
        State(inventory, Config())
        host = inventory.get_host('somehost')
        host.connect()

        stdout_mock = MagicMock()
        stdout_mock.channel.recv_exit_status.side_effect = [0, 1]
        fake_ssh_client().exec_command.return_value = MagicMock(), stdout_mock, MagicMock()

        fake_open = mock_open(read_data='test!')
        with patch('pyinfra.api.util.open', fake_open, create=True):
            status = host.get_file(
                'not-a-file', 'not-another-file',
                print_output=True,
                sudo=True,
                sudo_user='ubuntu',
            )

        assert status is False

        fake_ssh_client().exec_command.assert_has_calls([
            call((
                "sudo -H -n -u ubuntu sh -c 'cp not-a-file "
                "/tmp/pyinfra-e9c0d3c8ffca943daa0e75511b0a09c84b59c508 && chmod +r not-a-file'"
            ), get_pty=False),
            call((
                "sudo -H -n -u ubuntu sh -c 'rm -f "
                "/tmp/pyinfra-e9c0d3c8ffca943daa0e75511b0a09c84b59c508'"
            ), get_pty=False),
        ])

        fake_sftp_client.from_transport().getfo.assert_called_with(
            '/tmp/pyinfra-e9c0d3c8ffca943daa0e75511b0a09c84b59c508', fake_open(),
        )

    @patch('pyinfra.api.connectors.ssh.SSHClient')
    @patch('pyinfra.api.connectors.ssh.SFTPClient')
    def test_get_file_su_user(self, fake_sftp_client, fake_ssh_client):
        inventory = make_inventory(hosts=('somehost',))
        State(inventory, Config())
        host = inventory.get_host('somehost')
        host.connect()

        stdout_mock = MagicMock()
        stdout_mock.channel.recv_exit_status.return_value = 0
        fake_ssh_client().exec_command.return_value = MagicMock(), stdout_mock, MagicMock()

        fake_open = mock_open(read_data='test!')
        with patch('pyinfra.api.util.open', fake_open, create=True):
            status = host.get_file(
                'not-a-file', 'not-another-file',
                print_output=True,
                su_user='centos',
            )

        assert status is True

        fake_ssh_client().exec_command.assert_has_calls([
            call((
                "su centos -c 'sh -c '\"'\"'cp not-a-file "
                '/tmp/pyinfra-e9c0d3c8ffca943daa0e75511b0a09c84b59c508 && chmod +r '
                "not-a-file'\"'\"''"
            ), get_pty=False),
            call((
                "su centos -c 'sh -c '\"'\"'rm -f "
                "/tmp/pyinfra-e9c0d3c8ffca943daa0e75511b0a09c84b59c508'\"'\"''"
            ), get_pty=False),
        ])

        fake_sftp_client.from_transport().getfo.assert_called_with(
            '/tmp/pyinfra-e9c0d3c8ffca943daa0e75511b0a09c84b59c508', fake_open(),
        )

    @patch('pyinfra.api.connectors.ssh.SSHClient')
    @patch('pyinfra.api.connectors.ssh.SFTPClient')
    def test_get_sftp_fail(self, fake_sftp_client, fake_ssh_client):
        inventory = make_inventory(hosts=('anotherhost',))
        State(inventory, Config())
        host = inventory.get_host('anotherhost')
        host.connect()

        def raise_exception(*args, **kwargs):
            raise SSHException()

        fake_sftp_client.from_transport.side_effect = raise_exception

        fake_open = mock_open(read_data='test!')
        with patch('pyinfra.api.util.open', fake_open, create=True):
            with self.assertRaises(ConnectError):
                host.put_file(
                    'not-a-file', 'not-another-file',
                    print_output=True,
                )
