# encoding: utf-8

from socket import error as socket_error, gaierror
from unittest import TestCase
from unittest.mock import MagicMock, call, mock_open, patch

from paramiko import AuthenticationException, PasswordRequiredException, SSHException

import pyinfra
from pyinfra.api import Config, MaskString, State, StringCommand
from pyinfra.api.connect import connect_all
from pyinfra.api.exceptions import ConnectError, PyinfraError
from pyinfra.connectors.ssh import _get_sftp_connection

from ..util import make_inventory


def make_raise_exception_function(cls, *args, **kwargs):
    def handler(*a, **kw):
        raise cls(*args, **kwargs)

    return handler


@patch("pyinfra.connectors.ssh.SSHClient.get_transport", MagicMock())
@patch("pyinfra.connectors.ssh.open", mock_open(read_data="test!"), create=True)
class TestSSHConnector(TestCase):
    def setUp(self):
        self.fake_connect_patch = patch("pyinfra.connectors.ssh.SSHClient.connect")
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
        host = inventory.get_host("somehost")
        host.connect(reason=True)
        assert len(state.active_hosts) == 0

    def test_connect_all_password(self):
        inventory = make_inventory(override_data={"ssh_password": "test"})

        # Get a host
        somehost = inventory.get_host("somehost")
        assert somehost.data.ssh_password == "test"

        state = State(inventory, Config())
        connect_all(state)

        assert len(state.active_hosts) == 2

    @patch("pyinfra.connectors.ssh.path.isfile", lambda *args, **kwargs: True)
    @patch("pyinfra.connectors.ssh.RSAKey.from_private_key_file")
    def test_connect_exceptions(self, fake_key_open):
        for exception_class in (
            AuthenticationException,
            SSHException,
            gaierror,
            socket_error,
            EOFError,
        ):
            state = State(make_inventory(hosts=(("somehost", {"ssh_key": "testkey"}),)), Config())

            self.fake_connect_mock.side_effect = make_raise_exception_function(exception_class)

            with self.assertRaises(PyinfraError):
                connect_all(state)

            assert len(state.active_hosts) == 0

    # SSH key tests
    #

    def test_connect_with_rsa_ssh_key(self):
        state = State(make_inventory(hosts=(("somehost", {"ssh_key": "testkey"}),)), Config())

        with patch("pyinfra.connectors.ssh.path.isfile", lambda *args, **kwargs: True), patch(
            "pyinfra.connectors.ssh.RSAKey.from_private_key_file",
        ) as fake_key_open:

            fake_key = MagicMock()
            fake_key_open.return_value = fake_key

            connect_all(state)

            # Check the key was created properly
            fake_key_open.assert_called_with(filename="testkey")
            # Check the certificate file was then loaded
            fake_key.load_certificate.assert_called_with("testkey.pub")

            # And check the Paramiko SSH call was correct
            self.fake_connect_mock.assert_called_with(
                "somehost",
                allow_agent=False,
                look_for_keys=False,
                pkey=fake_key,
                timeout=10,
                username="vagrant",
                _pyinfra_ssh_forward_agent=None,
                _pyinfra_ssh_config_file=None,
                _pyinfra_ssh_known_hosts_file=None,
                _pyinfra_ssh_strict_host_key_checking=None,
                _pyinfra_ssh_paramiko_connect_kwargs=None,
            )

        # Check that loading the same key again is cached in the state
        second_state = State(
            make_inventory(hosts=(("somehost", {"ssh_key": "testkey"}),)),
            Config(),
        )
        second_state.private_keys = state.private_keys

        connect_all(second_state)

    def test_connect_with_rsa_ssh_key_password(self):
        state = State(
            make_inventory(
                hosts=(("somehost", {"ssh_key": "testkey", "ssh_key_password": "testpass"}),),
            ),
            Config(),
        )

        with patch("pyinfra.connectors.ssh.path.isfile", lambda *args, **kwargs: True), patch(
            "pyinfra.connectors.ssh.RSAKey.from_private_key_file",
        ) as fake_key_open:
            fake_key = MagicMock()

            def fake_key_open_fail(*args, **kwargs):
                if "password" not in kwargs:
                    raise PasswordRequiredException()
                return fake_key

            fake_key_open.side_effect = fake_key_open_fail

            connect_all(state)

            # Check the key was created properly
            fake_key_open.assert_called_with(filename="testkey", password="testpass")
            # Check the certificate file was then loaded
            fake_key.load_certificate.assert_called_with("testkey.pub")

    def test_connect_with_rsa_ssh_key_password_from_prompt(self):
        state = State(make_inventory(hosts=(("somehost", {"ssh_key": "testkey"}),)), Config())

        with patch("pyinfra.connectors.ssh.path.isfile", lambda *args, **kwargs: True), patch(
            "pyinfra.connectors.ssh.getpass",
            lambda *args, **kwargs: "testpass",
        ), patch(
            "pyinfra.connectors.ssh.RSAKey.from_private_key_file",
        ) as fake_key_open:
            fake_key = MagicMock()

            def fake_key_open_fail(*args, **kwargs):
                if "password" not in kwargs:
                    raise PasswordRequiredException()
                return fake_key

            fake_key_open.side_effect = fake_key_open_fail

            pyinfra.is_cli = True
            connect_all(state)
            pyinfra.is_cli = False

            # Check the key was created properly
            fake_key_open.assert_called_with(filename="testkey", password="testpass")
            # Check the certificate file was then loaded
            fake_key.load_certificate.assert_called_with("testkey.pub")

    def test_connect_with_rsa_ssh_key_missing_password(self):
        state = State(make_inventory(hosts=(("somehost", {"ssh_key": "testkey"}),)), Config())

        with patch("pyinfra.connectors.ssh.path.isfile", lambda *args, **kwargs: True), patch(
            "pyinfra.connectors.ssh.RSAKey.from_private_key_file",
        ) as fake_key_open:

            fake_key_open.side_effect = make_raise_exception_function(PasswordRequiredException)

            fake_key = MagicMock()
            fake_key_open.return_value = fake_key

            with self.assertRaises(PyinfraError) as e:
                connect_all(state)

            assert e.exception.args[0] == (
                "Private key file (testkey) is encrypted, set ssh_key_password " "to use this key"
            )

    def test_connect_with_rsa_ssh_key_wrong_password(self):
        state = State(
            make_inventory(
                hosts=(("somehost", {"ssh_key": "testkey", "ssh_key_password": "testpass"}),),
            ),
            Config(),
        )

        fake_fail_from_private_key_file = MagicMock()
        fake_fail_from_private_key_file.side_effect = make_raise_exception_function(SSHException)

        with patch("pyinfra.connectors.ssh.path.isfile", lambda *args, **kwargs: True), patch(
            "pyinfra.connectors.ssh.DSSKey.from_private_key_file",
            fake_fail_from_private_key_file,
        ), patch(
            "pyinfra.connectors.ssh.ECDSAKey.from_private_key_file",
            fake_fail_from_private_key_file,
        ), patch(
            "pyinfra.connectors.ssh.Ed25519Key.from_private_key_file",
            fake_fail_from_private_key_file,
        ), patch(
            "pyinfra.connectors.ssh.RSAKey.from_private_key_file",
        ) as fake_key_open:

            def fake_key_open_fail(*args, **kwargs):
                if "password" not in kwargs:
                    raise PasswordRequiredException
                raise SSHException

            fake_key_open.side_effect = fake_key_open_fail

            fake_key = MagicMock()
            fake_key_open.return_value = fake_key

            with self.assertRaises(PyinfraError) as e:
                connect_all(state)

            assert e.exception.args[0] == "Invalid private key file: testkey"

        assert fake_fail_from_private_key_file.call_count == 3

    def test_connect_with_dss_ssh_key(self):
        state = State(make_inventory(hosts=(("somehost", {"ssh_key": "testkey"}),)), Config())

        with patch("pyinfra.connectors.ssh.path.isfile", lambda *args, **kwargs: True), patch(
            "pyinfra.connectors.ssh.RSAKey.from_private_key_file",
        ) as fake_rsa_key_open, patch(
            "pyinfra.connectors.ssh.DSSKey.from_private_key_file",
        ) as fake_key_open:  # noqa

            fake_rsa_key_open.side_effect = make_raise_exception_function(SSHException)

            fake_key = MagicMock()
            fake_key_open.return_value = fake_key

            connect_all(state)

            # Check the key was created properly
            fake_key_open.assert_called_with(filename="testkey")

            # And check the Paramiko SSH call was correct
            self.fake_connect_mock.assert_called_with(
                "somehost",
                allow_agent=False,
                look_for_keys=False,
                pkey=fake_key,
                timeout=10,
                username="vagrant",
                _pyinfra_ssh_forward_agent=None,
                _pyinfra_ssh_config_file=None,
                _pyinfra_ssh_known_hosts_file=None,
                _pyinfra_ssh_strict_host_key_checking=None,
                _pyinfra_ssh_paramiko_connect_kwargs=None,
            )

        # Check that loading the same key again is cached in the state
        second_state = State(
            make_inventory(hosts=(("somehost", {"ssh_key": "testkey"}),)),
            Config(),
        )
        second_state.private_keys = state.private_keys

        connect_all(second_state)

    def test_connect_with_dss_ssh_key_password(self):
        state = State(
            make_inventory(
                hosts=(("somehost", {"ssh_key": "testkey", "ssh_key_password": "testpass"}),),
            ),
            Config(),
        )

        with patch("pyinfra.connectors.ssh.path.isfile", lambda *args, **kwargs: True), patch(
            "pyinfra.connectors.ssh.RSAKey.from_private_key_file",
        ) as fake_rsa_key_open, patch(
            "pyinfra.connectors.ssh.DSSKey.from_private_key_file",
        ) as fake_dss_key_open:  # noqa

            def fake_rsa_key_open_fail(*args, **kwargs):
                if "password" not in kwargs:
                    raise PasswordRequiredException
                raise SSHException

            fake_rsa_key_open.side_effect = fake_rsa_key_open_fail

            fake_dss_key = MagicMock()

            def fake_dss_key_func(*args, **kwargs):
                if "password" not in kwargs:
                    raise PasswordRequiredException
                return fake_dss_key

            fake_dss_key_open.side_effect = fake_dss_key_func

            connect_all(state)

            # Check the key was created properly
            fake_dss_key_open.assert_called_with(filename="testkey", password="testpass")

            # And check the Paramiko SSH call was correct
            self.fake_connect_mock.assert_called_with(
                "somehost",
                allow_agent=False,
                look_for_keys=False,
                pkey=fake_dss_key,
                timeout=10,
                username="vagrant",
                _pyinfra_ssh_forward_agent=None,
                _pyinfra_ssh_config_file=None,
                _pyinfra_ssh_known_hosts_file=None,
                _pyinfra_ssh_strict_host_key_checking=None,
                _pyinfra_ssh_paramiko_connect_kwargs=None,
            )

        # Check that loading the same key again is cached in the state
        second_state = State(
            make_inventory(hosts=(("somehost", {"ssh_key": "testkey"}),)),
            Config(),
        )
        second_state.private_keys = state.private_keys

        connect_all(second_state)

    def test_connect_with_missing_ssh_key(self):
        state = State(make_inventory(hosts=(("somehost", {"ssh_key": "testkey"}),)), Config())

        with self.assertRaises(PyinfraError) as e:
            connect_all(state)

        self.assertTrue(e.exception.args[0].startswith("No such private key file:"))

    # SSH command tests
    #

    @patch("pyinfra.connectors.ssh.SSHClient")
    def test_run_shell_command(self, fake_ssh_client):
        fake_ssh = MagicMock()
        fake_stdin = MagicMock()
        fake_stdout = MagicMock()
        fake_ssh.exec_command.return_value = fake_stdin, fake_stdout, MagicMock()

        fake_ssh_client.return_value = fake_ssh

        inventory = make_inventory(hosts=("somehost",))
        State(inventory, Config())
        host = inventory.get_host("somehost")
        host.connect()

        command = "echo Šablony"
        fake_stdout.channel.recv_exit_status.return_value = 0

        out = host.run_shell_command(command, stdin="hello", print_output=True)
        assert len(out) == 3

        status, stdout, stderr = out
        assert status is True
        fake_stdin.write.assert_called_with(b"hello\n")

        combined_out = host.run_shell_command(
            command,
            stdin="hello",
            print_output=True,
            return_combined_output=True,
        )
        assert len(combined_out) == 2

        fake_ssh.exec_command.assert_called_with("sh -c 'echo Šablony'", get_pty=False)

    @patch("pyinfra.connectors.ssh.click")
    @patch("pyinfra.connectors.ssh.SSHClient")
    def test_run_shell_command_masked(self, fake_ssh_client, fake_click):
        fake_ssh = MagicMock()
        fake_stdout = MagicMock()
        fake_ssh.exec_command.return_value = MagicMock(), fake_stdout, MagicMock()

        fake_ssh_client.return_value = fake_ssh

        inventory = make_inventory(hosts=("somehost",))
        State(inventory, Config())
        host = inventory.get_host("somehost")
        host.connect()

        command = StringCommand("echo", MaskString("top-secret-stuff"))
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

    @patch("pyinfra.connectors.ssh.SSHClient")
    def test_run_shell_command_success_exit_code(self, fake_ssh_client):
        fake_ssh = MagicMock()
        fake_stdout = MagicMock()
        fake_ssh.exec_command.return_value = MagicMock(), fake_stdout, MagicMock()

        fake_ssh_client.return_value = fake_ssh

        inventory = make_inventory(hosts=("somehost",))
        State(inventory, Config())
        host = inventory.get_host("somehost")
        host.connect()

        command = "echo hi"
        fake_stdout.channel.recv_exit_status.return_value = 1

        out = host.run_shell_command(command, success_exit_codes=[1])
        assert len(out) == 3
        assert out[0] is True

    @patch("pyinfra.connectors.ssh.SSHClient")
    def test_run_shell_command_error(self, fake_ssh_client):
        fake_ssh = MagicMock()
        fake_stdout = MagicMock()
        fake_ssh.exec_command.return_value = MagicMock(), fake_stdout, MagicMock()

        fake_ssh_client.return_value = fake_ssh

        inventory = make_inventory(hosts=("somehost",))
        state = State(inventory, Config())
        host = inventory.get_host("somehost")
        host.connect(state)

        command = "echo hi"
        fake_stdout.channel.recv_exit_status.return_value = 1

        out = host.run_shell_command(command)
        assert len(out) == 3
        assert out[0] is False

    @patch("pyinfra.connectors.util.getpass")
    @patch("pyinfra.connectors.ssh.SSHClient")
    def test_run_shell_command_sudo_password_prompt(
        self,
        fake_ssh_client,
        fake_getpass,
    ):
        fake_ssh = MagicMock()
        fake_stdout = MagicMock()
        fake_ssh.exec_command.return_value = MagicMock(), fake_stdout, MagicMock()

        fake_ssh_client.return_value = fake_ssh
        fake_getpass.return_value = "password"

        inventory = make_inventory(hosts=("somehost",))
        State(inventory, Config())
        host = inventory.get_host("somehost")
        host.connect()

        command = "echo Šablony"
        fake_stdout.__iter__.return_value = ["/tmp/pyinfra-sudo-askpass-XXXXXXXXXXXX"]
        fake_stdout.channel.recv_exit_status.return_value = 0

        out = host.run_shell_command(command, sudo=True, use_sudo_password=True, print_output=True)
        assert len(out) == 3

        status, stdout, stderr = out
        assert status is True

        fake_ssh.exec_command.assert_called_with(
            (
                "env SUDO_ASKPASS=/tmp/pyinfra-sudo-askpass-XXXXXXXXXXXX "
                "PYINFRA_SUDO_PASSWORD=password "
                "sudo -H -A -k sh -c 'echo Šablony'"
            ),
            get_pty=False,
        )

    @patch("pyinfra.connectors.util.getpass")
    @patch("pyinfra.connectors.ssh.SSHClient")
    def test_run_shell_command_sudo_password_automatic_prompt(
        self,
        fake_ssh_client,
        fake_getpass,
    ):
        fake_ssh = MagicMock()
        first_fake_stdout = MagicMock()
        second_fake_stdout = MagicMock()
        third_fake_stdout = MagicMock()

        first_fake_stdout.__iter__.return_value = ["sudo: a password is required\r"]
        second_fake_stdout.__iter__.return_value = ["/tmp/pyinfra-sudo-askpass-XXXXXXXXXXXX"]

        fake_ssh.exec_command.side_effect = [
            (MagicMock(), first_fake_stdout, MagicMock()),  # command w/o sudo password
            (MagicMock(), second_fake_stdout, MagicMock()),  # SUDO_ASKPASS_COMMAND
            (MagicMock(), third_fake_stdout, MagicMock()),  # command with sudo pw
        ]

        fake_ssh_client.return_value = fake_ssh
        fake_getpass.return_value = "password"

        inventory = make_inventory(hosts=("somehost",))
        State(inventory, Config())
        host = inventory.get_host("somehost")
        host.connect()

        command = "echo Šablony"
        first_fake_stdout.channel.recv_exit_status.return_value = 1
        second_fake_stdout.channel.recv_exit_status.return_value = 0
        third_fake_stdout.channel.recv_exit_status.return_value = 0

        out = host.run_shell_command(command, sudo=True, print_output=True)
        assert len(out) == 3

        status, stdout, stderr = out
        assert status is True

        fake_ssh.exec_command.assert_any_call(("sudo -H -n sh -c 'echo Šablony'"), get_pty=False)

        fake_ssh.exec_command.assert_called_with(
            (
                "env SUDO_ASKPASS=/tmp/pyinfra-sudo-askpass-XXXXXXXXXXXX "
                "PYINFRA_SUDO_PASSWORD=password "
                "sudo -H -A -k sh -c 'echo Šablony'"
            ),
            get_pty=False,
        )

    # SSH file put/get tests
    #

    @patch("pyinfra.connectors.ssh.SSHClient")
    @patch("pyinfra.connectors.util._get_sudo_password")
    def test_run_shell_command_retry_for_sudo_password(
        self,
        fake_get_sudo_password,
        fake_ssh_client,
    ):
        fake_get_sudo_password.return_value = "PASSWORD"

        fake_ssh = MagicMock()
        fake_stdin = MagicMock()
        fake_stdout = MagicMock()
        fake_stderr = ["sudo: a password is required"]
        fake_ssh.exec_command.return_value = fake_stdin, fake_stdout, fake_stderr

        fake_ssh_client.return_value = fake_ssh

        inventory = make_inventory(hosts=("somehost",))
        state = State(inventory, Config())
        host = inventory.get_host("somehost")
        host.connect(state)
        host.connector_data["sudo_askpass_path"] = "/tmp/pyinfra-sudo-askpass-XXXXXXXXXXXX"

        command = "echo hi"
        return_values = [1, 0]  # return 0 on the second call
        fake_stdout.channel.recv_exit_status.side_effect = lambda: return_values.pop(0)

        out = host.run_shell_command(command)
        assert len(out) == 3
        assert out[0] is True
        assert fake_get_sudo_password.called
        fake_ssh.exec_command.assert_called_with(
            "env SUDO_ASKPASS=/tmp/pyinfra-sudo-askpass-XXXXXXXXXXXX "
            "PYINFRA_SUDO_PASSWORD=PASSWORD sh -c 'echo hi'",
            get_pty=False,
        )

    # SSH file put/get tests
    #

    @patch("pyinfra.connectors.ssh.SSHClient")
    @patch("pyinfra.connectors.ssh.SFTPClient")
    def test_put_file(self, fake_sftp_client, fake_ssh_client):
        inventory = make_inventory(hosts=("anotherhost",))
        State(inventory, Config())
        host = inventory.get_host("anotherhost")
        host.connect()

        fake_open = mock_open(read_data="test!")
        with patch("pyinfra.api.util.open", fake_open, create=True):
            status = host.put_file(
                "not-a-file",
                "not-another-file",
                print_output=True,
            )

        assert status is True
        fake_sftp_client.from_transport().putfo.assert_called_with(
            fake_open(),
            "not-another-file",
        )

    @patch("pyinfra.connectors.ssh.SSHClient")
    @patch("pyinfra.connectors.ssh.SFTPClient")
    def test_put_file_sudo(self, fake_sftp_client, fake_ssh_client):
        inventory = make_inventory(hosts=("anotherhost",))
        State(inventory, Config())
        host = inventory.get_host("anotherhost")
        host.connect()

        stdout_mock = MagicMock()
        stdout_mock.channel.recv_exit_status.return_value = 0
        fake_ssh_client().exec_command.return_value = MagicMock(), stdout_mock, MagicMock()

        fake_open = mock_open(read_data="test!")
        with patch("pyinfra.api.util.open", fake_open, create=True):
            status = host.put_file(
                "not-a-file",
                "not another file",
                print_output=True,
                sudo=True,
                sudo_user="ubuntu",
            )

        assert status is True

        fake_ssh_client().exec_command.assert_called_with(
            ("sh -c 'rm -f " "/tmp/pyinfra-de01e82cb691e8a31369da3c7c8f17341c44ac24'"),
            get_pty=False,
        )

        fake_sftp_client.from_transport().putfo.assert_called_with(
            fake_open(),
            "/tmp/pyinfra-de01e82cb691e8a31369da3c7c8f17341c44ac24",
        )

    @patch("pyinfra.connectors.ssh.SSHClient")
    @patch("pyinfra.connectors.ssh.SFTPClient")
    def test_put_file_su_user_fail_acl(self, fake_sftp_client, fake_ssh_client):
        inventory = make_inventory(hosts=("anotherhost",))
        State(inventory, Config())
        host = inventory.get_host("anotherhost")
        host.connect()

        stdout_mock = MagicMock()
        stdout_mock.channel.recv_exit_status.return_value = 1
        fake_ssh_client().exec_command.return_value = MagicMock(), stdout_mock, MagicMock()

        fake_open = mock_open(read_data="test!")
        with patch("pyinfra.api.util.open", fake_open, create=True):
            status = host.put_file(
                "not-a-file",
                "not-another-file",
                print_output=True,
                su_user="centos",
            )

        assert status is False

        fake_ssh_client().exec_command.assert_called_with(
            (
                "sh -c 'setfacl -m u:centos:r "
                "/tmp/pyinfra-43db9984686317089fefcf2e38de527e4cb44487'"
            ),
            get_pty=False,
        )

        fake_sftp_client.from_transport().putfo.assert_called_with(
            fake_open(),
            "/tmp/pyinfra-43db9984686317089fefcf2e38de527e4cb44487",
        )

    @patch("pyinfra.connectors.ssh.SSHClient")
    @patch("pyinfra.connectors.ssh.SFTPClient")
    def test_put_file_su_user_fail_copy(self, fake_sftp_client, fake_ssh_client):
        inventory = make_inventory(hosts=("anotherhost",))
        State(inventory, Config())
        host = inventory.get_host("anotherhost")
        host.connect()

        stdout_mock = MagicMock()
        exit_codes = [0, 1]
        stdout_mock.channel.recv_exit_status.side_effect = lambda: exit_codes.pop(0)
        fake_ssh_client().exec_command.return_value = MagicMock(), stdout_mock, MagicMock()

        fake_open = mock_open(read_data="test!")
        with patch("pyinfra.api.util.open", fake_open, create=True):
            status = host.put_file(
                "not-a-file",
                "not-another-file",
                print_output=True,
                su_user="centos",
            )

        assert status is False

        fake_ssh_client().exec_command.assert_any_call(
            (
                "sh -c 'setfacl -m u:centos:r "
                "/tmp/pyinfra-43db9984686317089fefcf2e38de527e4cb44487'"
            ),
            get_pty=False,
        )

        fake_ssh_client().exec_command.assert_called_with(
            (
                "su centos -c 'sh -c '\"'\"'cp "
                "/tmp/pyinfra-43db9984686317089fefcf2e38de527e4cb44487 "
                "not-another-file'\"'\"''"
            ),
            get_pty=False,
        )

        fake_sftp_client.from_transport().putfo.assert_called_with(
            fake_open(),
            "/tmp/pyinfra-43db9984686317089fefcf2e38de527e4cb44487",
        )

    @patch("pyinfra.connectors.ssh.SSHClient")
    @patch("pyinfra.connectors.ssh.SFTPClient")
    def test_put_file_sudo_custom_temp_file(self, fake_sftp_client, fake_ssh_client):
        inventory = make_inventory(hosts=("anotherhost",))
        State(inventory, Config())
        host = inventory.get_host("anotherhost")
        host.connect()

        stdout_mock = MagicMock()
        stdout_mock.channel.recv_exit_status.return_value = 0
        fake_ssh_client().exec_command.return_value = MagicMock(), stdout_mock, MagicMock()

        fake_open = mock_open(read_data="test!")
        with patch("pyinfra.api.util.open", fake_open, create=True):
            status = host.put_file(
                "not-a-file",
                "not another file",
                print_output=True,
                sudo=True,
                sudo_user="ubuntu",
                remote_temp_filename="/a-different-tempfile",
            )

        assert status is True

        fake_ssh_client().exec_command.assert_called_with(
            ("sh -c 'rm -f " "/a-different-tempfile'"),
            get_pty=False,
        )

        fake_sftp_client.from_transport().putfo.assert_called_with(
            fake_open(),
            "/a-different-tempfile",
        )

    @patch("pyinfra.connectors.ssh.SSHClient")
    @patch("pyinfra.connectors.ssh.SFTPClient")
    def test_get_file(self, fake_sftp_client, fake_ssh_client):
        inventory = make_inventory(hosts=("somehost",))
        State(inventory, Config())
        host = inventory.get_host("somehost")
        host.connect()

        fake_open = mock_open(read_data="test!")
        with patch("pyinfra.api.util.open", fake_open, create=True):
            status = host.get_file(
                "not-a-file",
                "not-another-file",
                print_output=True,
            )

        assert status is True
        fake_sftp_client.from_transport().getfo.assert_called_with(
            "not-a-file",
            fake_open(),
        )

    @patch("pyinfra.connectors.ssh.SSHClient")
    @patch("pyinfra.connectors.ssh.SFTPClient")
    def test_get_file_sudo(self, fake_sftp_client, fake_ssh_client):
        inventory = make_inventory(hosts=("somehost",))
        State(inventory, Config())
        host = inventory.get_host("somehost")
        host.connect()

        stdout_mock = MagicMock()
        stdout_mock.channel.recv_exit_status.return_value = 0
        fake_ssh_client().exec_command.return_value = MagicMock(), stdout_mock, MagicMock()

        fake_open = mock_open(read_data="test!")
        with patch("pyinfra.api.util.open", fake_open, create=True):
            status = host.get_file(
                "not-a-file",
                "not-another-file",
                print_output=True,
                sudo=True,
                sudo_user="ubuntu",
            )

        assert status is True

        fake_ssh_client().exec_command.assert_has_calls(
            [
                call(
                    (
                        "sudo -H -n -u ubuntu sh -c 'cp not-a-file "
                        "/tmp/pyinfra-e9c0d3c8ffca943daa0e75511b0a09c84b59c508 && chmod +r not-a-file'"  # noqa
                    ),
                    get_pty=False,
                ),
                call(
                    (
                        "sudo -H -n -u ubuntu sh -c 'rm -f "
                        "/tmp/pyinfra-e9c0d3c8ffca943daa0e75511b0a09c84b59c508'"
                    ),
                    get_pty=False,
                ),
            ],
        )

        fake_sftp_client.from_transport().getfo.assert_called_with(
            "/tmp/pyinfra-e9c0d3c8ffca943daa0e75511b0a09c84b59c508",
            fake_open(),
        )

    @patch("pyinfra.connectors.ssh.SSHClient")
    def test_get_file_sudo_copy_fail(self, fake_ssh_client):
        inventory = make_inventory(hosts=("somehost",))
        State(inventory, Config())
        host = inventory.get_host("somehost")
        host.connect()

        stdout_mock = MagicMock()
        stdout_mock.channel.recv_exit_status.return_value = 1
        fake_ssh_client().exec_command.return_value = MagicMock(), stdout_mock, MagicMock()

        status = host.get_file(
            "not-a-file",
            "not-another-file",
            print_output=True,
            sudo=True,
            sudo_user="ubuntu",
        )

        assert status is False

        fake_ssh_client().exec_command.assert_has_calls(
            [
                call(
                    (
                        "sudo -H -n -u ubuntu sh -c 'cp not-a-file "
                        "/tmp/pyinfra-e9c0d3c8ffca943daa0e75511b0a09c84b59c508 && chmod +r not-a-file'"  # noqa
                    ),
                    get_pty=False,
                ),
            ],
        )

    @patch("pyinfra.connectors.ssh.SSHClient")
    @patch("pyinfra.connectors.ssh.SFTPClient")
    def test_get_file_sudo_remove_fail(self, fake_sftp_client, fake_ssh_client):
        inventory = make_inventory(hosts=("somehost",))
        State(inventory, Config())
        host = inventory.get_host("somehost")
        host.connect()

        stdout_mock = MagicMock()
        stdout_mock.channel.recv_exit_status.side_effect = [0, 1]
        fake_ssh_client().exec_command.return_value = MagicMock(), stdout_mock, MagicMock()

        fake_open = mock_open(read_data="test!")
        with patch("pyinfra.api.util.open", fake_open, create=True):
            status = host.get_file(
                "not-a-file",
                "not-another-file",
                print_output=True,
                sudo=True,
                sudo_user="ubuntu",
            )

        assert status is False

        fake_ssh_client().exec_command.assert_has_calls(
            [
                call(
                    (
                        "sudo -H -n -u ubuntu sh -c 'cp not-a-file "
                        "/tmp/pyinfra-e9c0d3c8ffca943daa0e75511b0a09c84b59c508 && chmod +r not-a-file'"  # noqa
                    ),
                    get_pty=False,
                ),
                call(
                    (
                        "sudo -H -n -u ubuntu sh -c 'rm -f "
                        "/tmp/pyinfra-e9c0d3c8ffca943daa0e75511b0a09c84b59c508'"
                    ),
                    get_pty=False,
                ),
            ],
        )

        fake_sftp_client.from_transport().getfo.assert_called_with(
            "/tmp/pyinfra-e9c0d3c8ffca943daa0e75511b0a09c84b59c508",
            fake_open(),
        )

    @patch("pyinfra.connectors.ssh.SSHClient")
    @patch("pyinfra.connectors.ssh.SFTPClient")
    def test_get_file_su_user(self, fake_sftp_client, fake_ssh_client):
        inventory = make_inventory(hosts=("somehost",))
        State(inventory, Config())
        host = inventory.get_host("somehost")
        host.connect()

        stdout_mock = MagicMock()
        stdout_mock.channel.recv_exit_status.return_value = 0
        fake_ssh_client().exec_command.return_value = MagicMock(), stdout_mock, MagicMock()

        fake_open = mock_open(read_data="test!")
        with patch("pyinfra.api.util.open", fake_open, create=True):
            status = host.get_file(
                "not-a-file",
                "not-another-file",
                print_output=True,
                su_user="centos",
            )

        assert status is True

        fake_ssh_client().exec_command.assert_has_calls(
            [
                call(
                    (
                        "su centos -c 'sh -c '\"'\"'cp not-a-file "
                        "/tmp/pyinfra-e9c0d3c8ffca943daa0e75511b0a09c84b59c508 && chmod +r "
                        "not-a-file'\"'\"''"
                    ),
                    get_pty=False,
                ),
                call(
                    (
                        "su centos -c 'sh -c '\"'\"'rm -f "
                        "/tmp/pyinfra-e9c0d3c8ffca943daa0e75511b0a09c84b59c508'\"'\"''"
                    ),
                    get_pty=False,
                ),
            ],
        )

        fake_sftp_client.from_transport().getfo.assert_called_with(
            "/tmp/pyinfra-e9c0d3c8ffca943daa0e75511b0a09c84b59c508",
            fake_open(),
        )

    @patch("pyinfra.connectors.ssh.SSHClient")
    @patch("pyinfra.connectors.ssh.SFTPClient")
    def test_get_sftp_fail(self, fake_sftp_client, fake_ssh_client):
        inventory = make_inventory(hosts=("anotherhost",))
        State(inventory, Config())
        host = inventory.get_host("anotherhost")
        host.connect()

        fake_sftp_client.from_transport.side_effect = make_raise_exception_function(SSHException)

        fake_open = mock_open(read_data="test!")
        with patch("pyinfra.api.util.open", fake_open, create=True):
            with self.assertRaises(ConnectError):
                host.put_file(
                    "not-a-file",
                    "not-another-file",
                    print_output=True,
                )
