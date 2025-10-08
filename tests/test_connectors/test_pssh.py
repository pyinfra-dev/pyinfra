# encoding: utf-8

from socket import error as socket_error, gaierror
from unittest import TestCase, mock

from pssh.exceptions import AuthenticationException, ConnectionErrorException, SessionError, Timeout

from pyinfra.api import Config, MaskString, State, StringCommand
from pyinfra.api.connect import connect_all
from pyinfra.api.exceptions import ConnectError, PyinfraError
from pyinfra.context import ctx_state

from ..util import make_inventory


def make_raise_exception_function(cls, *args, **kwargs):
    def handler(*a, **kw):
        raise cls(*args, **kwargs)

    return handler


class TestPSSHConnector(TestCase):
    def setUp(self):
        self.fake_ssh_client_patch = mock.patch("pyinfra.connectors.pssh.SSHClient")
        self.fake_ssh_client_mock = self.fake_ssh_client_patch.start()

    def tearDown(self):
        self.fake_ssh_client_patch.stop()

    def test_connect_all(self):
        inventory = make_inventory(hosts=(("@pssh/somehost", {}), ("@pssh/anotherhost", {})))
        state = State(inventory, Config())
        connect_all(state)
        assert len(state.active_hosts) == 2

    def test_connect_host(self):
        inventory = make_inventory(hosts=(("@pssh/somehost", {}),))
        state = State(inventory, Config())
        host = inventory.get_host("@pssh/somehost")
        host.connect(reason=True)
        assert len(state.active_hosts) == 0

    def test_connect_all_password(self):
        inventory = make_inventory(
            hosts=(("@pssh/somehost", {}), ("@pssh/anotherhost", {})),
            override_data={"ssh_password": "test"},
        )

        # Get a host
        somehost = inventory.get_host("@pssh/somehost")
        assert somehost.data.ssh_password == "test"

        state = State(inventory, Config())
        connect_all(state)

        assert len(state.active_hosts) == 2

    def test_connect_exceptions(self):
        for exception_class in (
            AuthenticationException,
            ConnectionErrorException,
            SessionError,
            gaierror,
            socket_error,
            EOFError,
        ):
            inventory = make_inventory(
                hosts=(("@pssh/somehost", {"ssh_key": "testkey"}),),
            )
            state = State(inventory, Config())

            # Mock SSHClient to raise exception on instantiation
            self.fake_ssh_client_mock.side_effect = make_raise_exception_function(exception_class)

            with self.assertRaises(PyinfraError):
                connect_all(state)

            assert len(state.active_hosts) == 0

            # Reset the side effect for next iteration
            self.fake_ssh_client_mock.side_effect = None

    def test_connect_with_ssh_key(self):
        inventory = make_inventory(hosts=(("@pssh/somehost", {"ssh_key": "testkey"}),))
        state = State(inventory, Config())

        fake_client = mock.MagicMock()
        self.fake_ssh_client_mock.return_value = fake_client

        connect_all(state)

        # Check the SSHClient was created with the correct parameters
        self.fake_ssh_client_mock.assert_called_with(
            host="somehost",
            allow_agent=True,
            pkey="testkey",
            timeout=10,
            user="vagrant",
        )

    def test_connect_with_ssh_key_password(self):
        inventory = make_inventory(
            hosts=(("@pssh/somehost", {"ssh_key": "testkey", "ssh_key_password": "testpass"}),),
        )
        state = State(inventory, Config())

        fake_client = mock.MagicMock()
        self.fake_ssh_client_mock.return_value = fake_client

        connect_all(state)

        # Check the SSHClient was created with the correct parameters
        self.fake_ssh_client_mock.assert_called_with(
            host="somehost",
            allow_agent=True,
            pkey="testkey",
            password="testpass",
            timeout=10,
            user="vagrant",
        )

    def test_connect_with_password(self):
        inventory = make_inventory(
            hosts=(("@pssh/somehost", {"ssh_password": "testpass"}),),
        )
        state = State(inventory, Config())

        fake_client = mock.MagicMock()
        self.fake_ssh_client_mock.return_value = fake_client

        connect_all(state)

        # Check the SSHClient was created with the correct parameters
        self.fake_ssh_client_mock.assert_called_with(
            host="somehost",
            allow_agent=True,
            password="testpass",
            timeout=10,
            user="vagrant",
        )

    def test_connect_with_custom_port(self):
        inventory = make_inventory(
            hosts=(("@pssh/somehost", {"ssh_port": 2222}),),
        )
        state = State(inventory, Config())

        fake_client = mock.MagicMock()
        self.fake_ssh_client_mock.return_value = fake_client

        connect_all(state)

        # Check the SSHClient was created with the correct port
        self.fake_ssh_client_mock.assert_called_with(
            host="somehost",
            allow_agent=True,
            port=2222,
            timeout=10,
            user="vagrant",
        )

    # Command execution tests

    def test_run_shell_command(self):
        fake_client = mock.MagicMock()
        fake_host_out = mock.MagicMock()
        fake_host_out.stdout = iter(["output line 1", "output line 2"])
        fake_host_out.stderr = iter([])
        fake_host_out.exit_code = 0
        fake_client.run_command.return_value = fake_host_out

        self.fake_ssh_client_mock.return_value = fake_client

        inventory = make_inventory(hosts=(("@pssh/somehost", {}),))
        State(inventory, Config())
        host = inventory.get_host("@pssh/somehost")
        host.connect()

        command = "echo test"
        status, output = host.run_shell_command(command, print_output=True)

        assert status is True
        assert len(output.stdout_lines) == 2
        assert output.stdout_lines[0] == "output line 1"
        assert output.stdout_lines[1] == "output line 2"

        fake_client.run_command.assert_called_with(
            "sh -c 'echo test'",
            use_pty=False,
            timeout=None,
        )

    def test_run_shell_command_with_unicode(self):
        fake_client = mock.MagicMock()
        fake_host_out = mock.MagicMock()
        fake_host_out.stdout = iter(["Šablony"])
        fake_host_out.stderr = iter([])
        fake_host_out.exit_code = 0
        fake_client.run_command.return_value = fake_host_out

        self.fake_ssh_client_mock.return_value = fake_client

        inventory = make_inventory(hosts=(("@pssh/somehost", {}),))
        State(inventory, Config())
        host = inventory.get_host("@pssh/somehost")
        host.connect()

        command = "echo Šablony"
        status, output = host.run_shell_command(command, print_output=True)

        assert status is True
        fake_client.run_command.assert_called_with(
            "sh -c 'echo Šablony'",
            use_pty=False,
            timeout=None,
        )

    @mock.patch("pyinfra.connectors.pssh.click")
    def test_run_shell_command_masked(self, fake_click):
        fake_client = mock.MagicMock()
        fake_host_out = mock.MagicMock()
        fake_host_out.stdout = iter([])
        fake_host_out.stderr = iter([])
        fake_host_out.exit_code = 0
        fake_client.run_command.return_value = fake_host_out

        self.fake_ssh_client_mock.return_value = fake_client

        inventory = make_inventory(hosts=(("@pssh/somehost", {}),))
        State(inventory, Config())
        host = inventory.get_host("@pssh/somehost")
        host.connect()

        command = StringCommand("echo", MaskString("top-secret-stuff"))
        status, output = host.run_shell_command(command, print_output=True, print_input=True)

        assert status is True

        fake_client.run_command.assert_called_with(
            "sh -c 'echo top-secret-stuff'",
            use_pty=False,
            timeout=None,
        )

        fake_click.echo.assert_called_with(
            "{0}>>> sh -c 'echo ***'".format(host.print_prefix),
            err=True,
        )

    def test_run_shell_command_success_exit_code(self):
        fake_client = mock.MagicMock()
        fake_host_out = mock.MagicMock()
        fake_host_out.stdout = iter([])
        fake_host_out.stderr = iter([])
        fake_host_out.exit_code = 1
        fake_client.run_command.return_value = fake_host_out

        self.fake_ssh_client_mock.return_value = fake_client

        inventory = make_inventory(hosts=(("@pssh/somehost", {}),))
        State(inventory, Config())
        host = inventory.get_host("@pssh/somehost")
        host.connect()

        command = "echo hi"
        status, output = host.run_shell_command(command, _success_exit_codes=[1])

        assert status is True

    def test_run_shell_command_error(self):
        fake_client = mock.MagicMock()
        fake_host_out = mock.MagicMock()
        fake_host_out.stdout = iter([])
        fake_host_out.stderr = iter(["error message"])
        fake_host_out.exit_code = 1
        fake_client.run_command.return_value = fake_host_out

        self.fake_ssh_client_mock.return_value = fake_client

        inventory = make_inventory(hosts=(("@pssh/somehost", {}),))
        state = State(inventory, Config())
        host = inventory.get_host("@pssh/somehost")
        host.connect(state)

        command = "echo hi"
        status, output = host.run_shell_command(command)

        assert status is False
        assert len(output.stderr_lines) == 1
        assert output.stderr_lines[0] == "error message"

    def test_run_shell_command_with_pty(self):
        fake_client = mock.MagicMock()
        fake_host_out = mock.MagicMock()
        fake_host_out.stdout = iter([])
        fake_host_out.stderr = iter([])
        fake_host_out.exit_code = 0
        fake_client.run_command.return_value = fake_host_out

        self.fake_ssh_client_mock.return_value = fake_client

        inventory = make_inventory(hosts=(("@pssh/somehost", {}),))
        State(inventory, Config())
        host = inventory.get_host("@pssh/somehost")
        host.connect()

        command = "echo test"
        status, output = host.run_shell_command(command, _get_pty=True)

        assert status is True
        fake_client.run_command.assert_called_with(
            "sh -c 'echo test'",
            use_pty=True,
            timeout=None,
        )

    def test_run_shell_command_with_timeout(self):
        fake_client = mock.MagicMock()
        fake_host_out = mock.MagicMock()
        fake_host_out.stdout = iter([])
        fake_host_out.stderr = iter([])
        fake_host_out.exit_code = 0
        fake_client.run_command.return_value = fake_host_out

        self.fake_ssh_client_mock.return_value = fake_client

        inventory = make_inventory(hosts=(("@pssh/somehost", {}),))
        State(inventory, Config())
        host = inventory.get_host("@pssh/somehost")
        host.connect()

        command = "echo test"
        status, output = host.run_shell_command(command, _timeout=30)

        assert status is True
        fake_client.run_command.assert_called_with(
            "sh -c 'echo test'",
            use_pty=False,
            timeout=30,
        )

    def test_run_shell_command_timeout_exception(self):
        fake_client = mock.MagicMock()
        fake_host_out = mock.MagicMock()

        # Make stderr iteration raise Timeout
        def stderr_with_timeout():
            yield "some output"
            raise Timeout("Command timed out")

        fake_host_out.stdout = iter([])
        fake_host_out.stderr = stderr_with_timeout()
        fake_host_out.exit_code = None
        fake_client.run_command.return_value = fake_host_out

        self.fake_ssh_client_mock.return_value = fake_client

        inventory = make_inventory(hosts=(("@pssh/somehost", {}),))
        State(inventory, Config())
        host = inventory.get_host("@pssh/somehost")
        host.connect()

        command = "sleep 100"
        # The timeout is caught and logged as a warning, not raised as an exception
        status, output = host.run_shell_command(command, _timeout=1)
        # Should fail with exit code -1
        assert status is False

    @mock.patch("pyinfra.connectors.util.getpass")
    def test_run_shell_command_sudo_password_automatic_prompt(self, fake_getpass):
        fake_client = mock.MagicMock()

        # First call: command fails without sudo password
        first_fake_host_out = mock.MagicMock()
        first_fake_host_out.stdout = iter(["sudo: a password is required\r"])
        first_fake_host_out.stderr = iter([])
        first_fake_host_out.exit_code = 1

        # Second call: create askpass script
        second_fake_host_out = mock.MagicMock()
        second_fake_host_out.stdout = iter(["/tmp/pyinfra-sudo-askpass-XXXXXXXXXXXX"])
        second_fake_host_out.stderr = iter([])
        second_fake_host_out.exit_code = 0

        # Third call: command succeeds with sudo password
        third_fake_host_out = mock.MagicMock()
        third_fake_host_out.stdout = iter(["success"])
        third_fake_host_out.stderr = iter([])
        third_fake_host_out.exit_code = 0

        fake_client.run_command.side_effect = [
            first_fake_host_out,
            second_fake_host_out,
            third_fake_host_out,
        ]

        self.fake_ssh_client_mock.return_value = fake_client
        fake_getpass.return_value = "password"

        inventory = make_inventory(hosts=(("@pssh/somehost", {}),))
        State(inventory, Config())
        host = inventory.get_host("@pssh/somehost")
        host.connect()

        command = "echo Šablony"
        status, output = host.run_shell_command(command, _sudo=True, print_output=True)

        assert status is True
        assert fake_getpass.called

    # File transfer tests

    def test_put_file(self):
        fake_client = mock.MagicMock()
        self.fake_ssh_client_mock.return_value = fake_client

        inventory = make_inventory(hosts=(("@pssh/anotherhost", {}),))
        state = State(inventory, Config())
        host = inventory.get_host("@pssh/anotherhost")
        host.connect()

        fake_open = mock.mock_open(read_data="test!")
        with mock.patch("pyinfra.api.util.open", fake_open, create=True):
            with ctx_state.use(state):
                status = host.put_file(
                    "not-a-file",
                    "not-another-file",
                    print_output=True,
                )

        assert status is True
        fake_client.copy_file.assert_called_once()

    def test_put_file_sudo(self):
        fake_client = mock.MagicMock()
        fake_host_out = mock.MagicMock()
        fake_host_out.stdout = iter([])
        fake_host_out.stderr = iter([])
        fake_host_out.exit_code = 0
        fake_client.run_command.return_value = fake_host_out

        self.fake_ssh_client_mock.return_value = fake_client

        inventory = make_inventory(hosts=(("@pssh/anotherhost", {}),))
        state = State(inventory, Config())
        host = inventory.get_host("@pssh/anotherhost")
        host.connect()

        fake_open = mock.mock_open(read_data="test!")
        with mock.patch("pyinfra.api.util.open", fake_open, create=True):
            with ctx_state.use(state):
                status = host.put_file(
                    "not-a-file",
                    "not another file",
                    print_output=True,
                    _sudo=True,
                    _sudo_user="ubuntu",
                )

        assert status is True

        # Should have called copy_file for the temp file
        assert fake_client.copy_file.called

        # Should have run commands to set ACL, copy, and remove temp file
        assert fake_client.run_command.call_count == 3

    def test_put_file_doas(self):
        fake_client = mock.MagicMock()
        fake_host_out = mock.MagicMock()
        fake_host_out.stdout = iter([])
        fake_host_out.stderr = iter([])
        fake_host_out.exit_code = 0
        fake_client.run_command.return_value = fake_host_out

        self.fake_ssh_client_mock.return_value = fake_client

        inventory = make_inventory(hosts=(("@pssh/anotherhost", {}),))
        state = State(inventory, Config())
        host = inventory.get_host("@pssh/anotherhost")
        host.connect()

        fake_open = mock.mock_open(read_data="test!")
        with mock.patch("pyinfra.api.util.open", fake_open, create=True):
            with ctx_state.use(state):
                status = host.put_file(
                    "not-a-file",
                    "not another file",
                    print_output=True,
                    _doas=True,
                    _doas_user="ubuntu",
                )

        assert status is True
        assert fake_client.copy_file.called

    def test_put_file_su_user_fail_acl(self):
        fake_client = mock.MagicMock()
        fake_host_out = mock.MagicMock()
        fake_host_out.stdout = iter([])
        fake_host_out.stderr = iter(["setfacl: Operation not permitted"])
        fake_host_out.exit_code = 1
        fake_client.run_command.return_value = fake_host_out

        self.fake_ssh_client_mock.return_value = fake_client

        inventory = make_inventory(hosts=(("@pssh/anotherhost", {}),))
        state = State(inventory, Config())
        host = inventory.get_host("@pssh/anotherhost")
        host.connect()

        fake_open = mock.mock_open(read_data="test!")
        with mock.patch("pyinfra.api.util.open", fake_open, create=True):
            with ctx_state.use(state):
                status = host.put_file(
                    "not-a-file",
                    "not-another-file",
                    print_output=True,
                    _su_user="centos",
                )

        assert status is False

    def test_get_file(self):
        fake_client = mock.MagicMock()
        self.fake_ssh_client_mock.return_value = fake_client

        inventory = make_inventory(hosts=(("@pssh/somehost", {}),))
        state = State(inventory, Config())
        host = inventory.get_host("@pssh/somehost")
        host.connect()

        fake_open = mock.mock_open(read_data="test!")
        with mock.patch("pyinfra.api.util.open", fake_open, create=True):
            with ctx_state.use(state):
                status = host.get_file(
                    "not-a-file",
                    "not-another-file",
                    print_output=True,
                )

        assert status is True
        fake_client.copy_remote_file.assert_called_once_with("not-a-file", "not-another-file")

    def test_get_file_sudo(self):
        fake_client = mock.MagicMock()
        fake_host_out = mock.MagicMock()
        fake_host_out.stdout = iter([])
        fake_host_out.stderr = iter([])
        fake_host_out.exit_code = 0
        fake_client.run_command.return_value = fake_host_out

        self.fake_ssh_client_mock.return_value = fake_client

        inventory = make_inventory(hosts=(("@pssh/somehost", {}),))
        state = State(inventory, Config())
        host = inventory.get_host("@pssh/somehost")
        host.connect()

        fake_open = mock.mock_open(read_data="test!")
        with mock.patch("pyinfra.api.util.open", fake_open, create=True):
            with ctx_state.use(state):
                status = host.get_file(
                    "not-a-file",
                    "not-another-file",
                    print_output=True,
                    _sudo=True,
                    _sudo_user="ubuntu",
                )

        assert status is True

        # Should have called copy_remote_file for the temp file
        assert fake_client.copy_remote_file.called

        # Should have run commands to copy and remove temp file
        assert fake_client.run_command.call_count == 2

    def test_get_file_sudo_copy_fail(self):
        fake_client = mock.MagicMock()
        fake_host_out = mock.MagicMock()
        fake_host_out.stdout = iter([])
        fake_host_out.stderr = iter(["cp: cannot stat"])
        fake_host_out.exit_code = 1
        fake_client.run_command.return_value = fake_host_out

        self.fake_ssh_client_mock.return_value = fake_client

        inventory = make_inventory(hosts=(("@pssh/somehost", {}),))
        state = State(inventory, Config())
        host = inventory.get_host("@pssh/somehost")
        host.connect()

        with ctx_state.use(state):
            status = host.get_file(
                "not-a-file",
                "not-another-file",
                print_output=True,
                _sudo=True,
                _sudo_user="ubuntu",
            )

        assert status is False

    def test_get_file_sudo_remove_fail(self):
        fake_client = mock.MagicMock()

        # First call (copy): success
        first_fake_host_out = mock.MagicMock()
        first_fake_host_out.stdout = iter([])
        first_fake_host_out.stderr = iter([])
        first_fake_host_out.exit_code = 0

        # Second call (remove): fail
        second_fake_host_out = mock.MagicMock()
        second_fake_host_out.stdout = iter([])
        second_fake_host_out.stderr = iter(["rm: cannot remove"])
        second_fake_host_out.exit_code = 1

        fake_client.run_command.side_effect = [first_fake_host_out, second_fake_host_out]

        self.fake_ssh_client_mock.return_value = fake_client

        inventory = make_inventory(hosts=(("@pssh/somehost", {}),))
        state = State(inventory, Config())
        host = inventory.get_host("@pssh/somehost")
        host.connect()

        fake_open = mock.mock_open(read_data="test!")
        with mock.patch("pyinfra.api.util.open", fake_open, create=True):
            with ctx_state.use(state):
                status = host.get_file(
                    "not-a-file",
                    "not-another-file",
                    print_output=True,
                    _sudo=True,
                    _sudo_user="ubuntu",
                )

        assert status is False

    def test_get_file_su_user(self):
        fake_client = mock.MagicMock()
        fake_host_out = mock.MagicMock()
        fake_host_out.stdout = iter([])
        fake_host_out.stderr = iter([])
        fake_host_out.exit_code = 0
        fake_client.run_command.return_value = fake_host_out

        self.fake_ssh_client_mock.return_value = fake_client

        inventory = make_inventory(hosts=(("@pssh/somehost", {}),))
        state = State(inventory, Config())
        host = inventory.get_host("@pssh/somehost")
        host.connect()

        fake_open = mock.mock_open(read_data="test!")
        with mock.patch("pyinfra.api.util.open", fake_open, create=True):
            with ctx_state.use(state):
                status = host.get_file(
                    "not-a-file",
                    "not-another-file",
                    print_output=True,
                    _su_user="centos",
                )

        assert status is True
        assert fake_client.copy_remote_file.called

    # Connection retry tests

    @mock.patch("pyinfra.connectors.pssh.sleep")
    def test_pssh_connect_fail_retry(self, fake_sleep):
        for exception_class in (
            SessionError,
            ConnectionErrorException,
            gaierror,
            socket_error,
            EOFError,
        ):
            fake_sleep.reset_mock()
            self.fake_ssh_client_mock.reset_mock()

            inventory = make_inventory(
                hosts=(("@pssh/unresponsivehost", {}),),
                override_data={"ssh_connect_retries": 1},
            )
            State(inventory, Config())

            unresponsivehost = inventory.get_host("@pssh/unresponsivehost")
            assert unresponsivehost.data.ssh_connect_retries == 1

            self.fake_ssh_client_mock.side_effect = exception_class()

            with self.assertRaises(ConnectError):
                unresponsivehost.connect(show_errors=False, raise_exceptions=True)

            fake_sleep.assert_called_once()
            assert self.fake_ssh_client_mock.call_count == 2

            # Reset side effect for next iteration
            self.fake_ssh_client_mock.side_effect = None

    @mock.patch("pyinfra.connectors.pssh.sleep")
    def test_pssh_connect_fail_success(self, fake_sleep):
        for exception_class in (
            SessionError,
            ConnectionErrorException,
            gaierror,
            socket_error,
            EOFError,
        ):
            fake_sleep.reset_mock()
            self.fake_ssh_client_mock.reset_mock()

            inventory = make_inventory(
                hosts=(("@pssh/unresponsivehost", {}),),
                override_data={"ssh_connect_retries": 1},
            )
            State(inventory, Config())

            unresponsivehost = inventory.get_host("@pssh/unresponsivehost")
            assert unresponsivehost.data.ssh_connect_retries == 1

            fake_client = mock.MagicMock()
            self.fake_ssh_client_mock.side_effect = [
                exception_class(),
                fake_client,
            ]

            unresponsivehost.connect(show_errors=False, raise_exceptions=True)
            fake_sleep.assert_called_once()
            assert self.fake_ssh_client_mock.call_count == 2

            # Reset side effect for next iteration
            self.fake_ssh_client_mock.side_effect = None

    def test_disconnect(self):
        fake_client = mock.MagicMock()
        self.fake_ssh_client_mock.return_value = fake_client

        inventory = make_inventory(hosts=(("@pssh/somehost", {}),))
        State(inventory, Config())
        host = inventory.get_host("@pssh/somehost")
        host.connect()

        # Disconnect should call disconnect on the client
        host.disconnect()
        fake_client.disconnect.assert_called_once()

    def test_make_names_data(self):
        from pyinfra.connectors.pssh import PSSHConnector

        # Test the static method that generates inventory targets
        results = list(PSSHConnector.make_names_data("testhost"))
        assert len(results) == 1
        assert results[0][0] == "@pssh/testhost"
        assert results[0][1] == {"ssh_hostname": "testhost"}
        assert results[0][2] == []
