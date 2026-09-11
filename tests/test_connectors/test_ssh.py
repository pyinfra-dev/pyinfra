import asyncio
from pathlib import Path
from socket import gaierror
from tempfile import TemporaryDirectory
from unittest import mock

import asyncssh

import pyinfra
from pyinfra.api import Config, Host, HiddenValue, State, StringCommand
from pyinfra.api.concurrency import async_def
from pyinfra.api.connect import connect_all
from pyinfra.api.exceptions import ConnectError, PyinfraError
from pyinfra.connectors.ssh_hostkeys import PyinfraSSHClient
from pyinfra.context import ctx_state

from ..fake_ssh import AsyncPatchSSHTestCase, FakeCertificate, FakeKey
from ..util import make_inventory

ANY_FILE_EXISTS = mock.patch(
    "pyinfra.connectors.ssh_util.Path.is_file", lambda *args, **kwargs: True
)

PASSPHRASE_REQUIRED = asyncssh.KeyImportError(
    "Passphrase must be specified to import encrypted private keys",
)


class TestSSHConnector(AsyncPatchSSHTestCase):
    async def connect_host(self, host_data=None, hosts=("somehost",), config=None):
        hosts = tuple((host, host_data or {}) for host in hosts)
        inventory = make_inventory(hosts=hosts)
        state = State(inventory, config or Config(TEMP_DIR="/tmp"))
        host = inventory.get_host(hosts[0][0])
        await async_def(host.connect)
        return state, host, self.fake_ssh.connection

    # Connection tests
    #

    async def test_connect_all(self):
        inventory = make_inventory()
        state = State(inventory, Config())
        await connect_all(state)

        assert len(state.active_hosts) == 2
        assert len(self.fake_ssh.connect_calls) == 2
        assert {call["host"] for call in self.fake_ssh.connect_calls} == {"somehost", "anotherhost"}

    async def test_connect_host(self):
        inventory = make_inventory()
        state = State(inventory, Config())
        host = inventory.get_host("somehost")
        await async_def(host.connect, reason=True)

        assert host.connected is True
        assert len(state.active_hosts) == 0

    async def test_connect_kwargs(self):
        with mock.patch("pyinfra.connectors.ssh.os.path.isfile", return_value=False):
            await self.connect_host()

        kwargs = self.fake_ssh.connect_calls[0]
        assert kwargs["host"] == "somehost"
        assert kwargs["username"] == "vagrant"
        assert kwargs["connect_timeout"] == 10
        assert kwargs["config"] == ()
        assert "password" not in kwargs
        assert "client_keys" not in kwargs
        assert "agent_path" not in kwargs
        assert "agent_forwarding" not in kwargs
        # Host key policy is applied via our own client
        assert kwargs["known_hosts"] == b""
        client = kwargs["client_factory"]()
        assert isinstance(client, PyinfraSSHClient)
        assert client.policy == "accept-new"
        assert client.known_hosts_files == [str(Path("~/.ssh/known_hosts").expanduser())]

    async def test_connect_all_password(self):
        inventory = make_inventory(override_data={"ssh_password": "test"})

        somehost = inventory.get_host("somehost")
        assert somehost.data.ssh_password == "test"

        state = State(inventory, Config())
        await connect_all(state)

        assert len(state.active_hosts) == 2
        assert self.fake_ssh.connect_calls[0]["password"] == "test"

    async def test_connect_options(self):
        await self.connect_host(
            {
                "ssh_port": 2222,
                "ssh_forward_agent": True,
                "ssh_known_hosts_file": "/does/not/exist/known_hosts",
                "ssh_strict_host_key_checking": "yes",
                "ssh_connect_kwargs": {"keepalive_interval": 5},
            },
        )

        kwargs = self.fake_ssh.connect_calls[0]
        assert kwargs["port"] == 2222
        assert kwargs["agent_forwarding"] is True
        assert kwargs["keepalive_interval"] == 5
        # No known hosts file exists yet, so asyncssh gets none & we create the file on accept
        assert kwargs["known_hosts"] == b""
        client = kwargs["client_factory"]()
        assert client.policy == "yes"
        assert client.known_hosts_files == ["/does/not/exist/known_hosts"]

    async def test_connect_existing_known_hosts_file(self):
        with TemporaryDirectory() as temp_dir:
            known_hosts = Path(temp_dir) / "known_hosts"
            known_hosts.write_text("")

            await self.connect_host({"ssh_known_hosts_file": str(known_hosts)})

            assert self.fake_ssh.connect_calls[0]["known_hosts"] == [str(known_hosts)]

    async def test_connect_ssh_config_file(self):
        with TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "config"
            config_file.write_text("Host somehost\n")

            await self.connect_host({"ssh_config_file": str(config_file)})
            assert self.fake_ssh.connect_calls[0]["config"] == [str(config_file)]

            # A missing config file is ignored (rather than falling back to ~/.ssh/config)
            await self.connect_host({"ssh_config_file": str(Path(temp_dir) / "missing")})
            assert self.fake_ssh.connect_calls[1]["config"] is None

    async def test_connect_no_agent_no_keys(self):
        await self.connect_host({"ssh_allow_agent": False, "ssh_look_for_keys": False})

        kwargs = self.fake_ssh.connect_calls[0]
        assert kwargs["agent_path"] is None
        assert kwargs["client_keys"] == []

    async def test_connect_exceptions(self):
        for exception in (
            asyncssh.PermissionDenied("denied"),
            asyncssh.HostKeyNotVerifiable("bad key"),
            asyncssh.Error(1, "boom"),
            gaierror(),
            ConnectionRefusedError(),
            asyncio.TimeoutError(),
        ):
            state = State(make_inventory(hosts=("somehost",)), Config())

            self.fake_ssh.connect_side_effect = exception

            with self.assertRaises(PyinfraError):
                await connect_all(state)

            assert len(state.active_hosts) == 0

    async def test_connect_error_messages(self):
        for exception, message in (
            (asyncssh.PermissionDenied("denied"), "Authentication error (username=vagrant)"),
            (asyncssh.HostKeyNotVerifiable("bad key"), "SSH host key error"),
            (asyncssh.Error(1, "boom"), "SSH error"),
            (gaierror(), "Could not resolve hostname"),
            (ConnectionRefusedError(), "Could not connect ("),
            (asyncio.TimeoutError(), "Could not connect (timeout)"),
        ):
            inventory = make_inventory(hosts=("somehost",))
            State(inventory, Config())
            host = inventory.get_host("somehost")

            self.fake_ssh.connect_side_effect = exception

            with self.assertRaises(ConnectError) as e:
                await async_def(host.connect, show_errors=False, raise_exceptions=True)

            assert e.exception.args[0].startswith(message), e.exception.args[0]

    # SSH key tests
    #

    @ANY_FILE_EXISTS
    async def test_connect_with_ssh_key(self):
        state, _, _ = await self.connect_host({"ssh_key": "testkey"})

        kwargs = self.fake_ssh.connect_calls[0]
        ((key, certificate),) = kwargs["client_keys"]
        assert isinstance(key, FakeKey)
        assert key.filename == "testkey"
        assert key.passphrase is None
        assert isinstance(certificate, FakeCertificate)
        assert certificate.filename == "testkey-cert.pub"
        # The agent stays available for forwarding but is not used to authenticate
        assert kwargs["agent_identities"] == []
        assert "agent_path" not in kwargs

        # Check that loading the same key again is cached in the state
        inventory = make_inventory(hosts=(("somehost", {"ssh_key": "testkey"}),))
        second_state = State(inventory, Config())
        second_state.private_keys = state.private_keys

        with mock.patch("pyinfra.connectors.ssh_util.load_key_with_certificate") as fake_load:
            await connect_all(second_state)

        fake_load.assert_not_called()
        assert self.fake_ssh.connect_calls[1]["client_keys"] == kwargs["client_keys"]

    @ANY_FILE_EXISTS
    async def test_connect_with_ssh_key_password(self):
        await self.connect_host({"ssh_key": "testkey", "ssh_key_password": "testpass"})

        ((key, _),) = self.fake_ssh.connect_calls[0]["client_keys"]
        assert key.passphrase == "testpass"

    @ANY_FILE_EXISTS
    async def test_connect_with_ssh_key_password_from_prompt(self):
        def read_private_key(filename, passphrase=None):
            if passphrase is None:
                raise PASSPHRASE_REQUIRED
            return FakeKey(filename, passphrase)

        with (
            mock.patch("pyinfra.connectors.ssh_util.read_private_key", read_private_key),
            mock.patch("pyinfra.connectors.ssh_util.getpass", lambda *args, **kwargs: "testpass"),
        ):
            pyinfra.is_cli = True
            try:
                await self.connect_host({"ssh_key": "testkey"})
            finally:
                pyinfra.is_cli = False

        ((key, _),) = self.fake_ssh.connect_calls[0]["client_keys"]
        assert key.passphrase == "testpass"

    @ANY_FILE_EXISTS
    async def test_connect_with_ssh_key_missing_password(self):
        state = State(make_inventory(hosts=(("somehost", {"ssh_key": "testkey"}),)), Config())

        def read_private_key(filename, passphrase=None):
            raise PASSPHRASE_REQUIRED

        with mock.patch("pyinfra.connectors.ssh_util.read_private_key", read_private_key):
            with self.assertRaises(PyinfraError) as e:
                await connect_all(state)

        assert e.exception.args[0] == (
            "Private key file (testkey) is encrypted, set ssh_key_password to use this key"
        )

    @ANY_FILE_EXISTS
    async def test_connect_with_ssh_key_wrong_password(self):
        state = State(
            make_inventory(hosts=(("somehost", {"ssh_key": "testkey", "ssh_key_password": "x"}),)),
            Config(),
        )

        def read_private_key(filename, passphrase=None):
            raise asyncssh.KeyEncryptionError("Incorrect passphrase")

        with mock.patch("pyinfra.connectors.ssh_util.read_private_key", read_private_key):
            with self.assertRaises(PyinfraError) as e:
                await connect_all(state)

        assert e.exception.args[0] == "Incorrect password for private key: testkey"

    @ANY_FILE_EXISTS
    async def test_connect_with_invalid_ssh_key(self):
        state = State(make_inventory(hosts=(("somehost", {"ssh_key": "testkey"}),)), Config())

        def read_private_key(filename, passphrase=None):
            raise asyncssh.KeyImportError("Invalid key")

        with mock.patch("pyinfra.connectors.ssh_util.read_private_key", read_private_key):
            with self.assertRaises(PyinfraError) as e:
                await connect_all(state)

        assert e.exception.args[0] == "Invalid private key file: testkey"

    async def test_connect_with_missing_ssh_key(self):
        state = State(make_inventory(hosts=(("somehost", {"ssh_key": "testkey"}),)), Config())

        with self.assertRaises(PyinfraError) as e:
            await connect_all(state)

        self.assertTrue(e.exception.args[0].startswith("No such private key file:"))

    # Connection retry tests
    #

    async def test_ssh_connect_fail_retry(self):
        for exception in (
            asyncssh.Error(1, "boom"),
            gaierror(),
            ConnectionRefusedError(),
            asyncio.TimeoutError(),
        ):
            inventory = make_inventory(
                hosts=("unresposivehost",), override_data={"ssh_connect_retries": 1}
            )
            State(inventory, Config())

            unresposivehost = inventory.get_host("unresposivehost")
            assert unresposivehost.data.ssh_connect_retries == 1

            self.fake_ssh.connect_calls = []
            self.fake_ssh.connect_side_effect = [exception, exception]

            with mock.patch("pyinfra.connectors.ssh.asyncio.sleep", new=mock.AsyncMock()) as sleep:
                with self.assertRaises(ConnectError):
                    await async_def(
                        unresposivehost.connect, show_errors=False, raise_exceptions=True
                    )

            sleep.assert_called_once()
            assert len(self.fake_ssh.connect_calls) == 2

    async def test_ssh_connect_fail_success(self):
        for exception in (
            asyncssh.Error(1, "boom"),
            gaierror(),
            ConnectionRefusedError(),
            asyncio.TimeoutError(),
        ):
            inventory = make_inventory(
                hosts=("unresposivehost",), override_data={"ssh_connect_retries": 1}
            )
            State(inventory, Config())

            unresposivehost = inventory.get_host("unresposivehost")

            self.fake_ssh.connect_calls = []
            self.fake_ssh.connect_side_effect = [exception]

            with mock.patch("pyinfra.connectors.ssh.asyncio.sleep", new=mock.AsyncMock()) as sleep:
                await async_def(unresposivehost.connect, show_errors=False, raise_exceptions=True)

            sleep.assert_called_once()
            assert len(self.fake_ssh.connect_calls) == 2
            assert unresposivehost.connected is True

    async def test_ssh_connect_auth_failure_not_retried(self):
        inventory = make_inventory(hosts=("somehost",), override_data={"ssh_connect_retries": 3})
        State(inventory, Config())
        host = inventory.get_host("somehost")

        self.fake_ssh.connect_side_effect = asyncssh.PermissionDenied("denied")

        with self.assertRaises(ConnectError):
            await async_def(host.connect, show_errors=False, raise_exceptions=True)

        assert len(self.fake_ssh.connect_calls) == 1

    async def test_disconnect(self):
        _, host, connection = await self.connect_host()

        await async_def(host.disconnect)

        assert connection.closed is True
        assert host.connected is False
        assert host.connector.client is None

    # SSH command tests
    #

    async def test_run_shell_command(self):
        _, host, connection = await self.connect_host()

        command = "echo Šablony"

        out = await async_def(host.run_shell_command, command, _stdin="hello", print_output=True)
        assert len(out) == 2

        status, output = out
        assert status is True

        process = connection.processes[-1]
        assert process.command == "sh -c 'echo Šablony'"
        assert process.term_type is None
        assert process.stdin.written == [b"hello\n"]
        assert process.stdin.eof is True

    async def test_run_shell_command_pty(self):
        _, host, connection = await self.connect_host()

        await async_def(host.run_shell_command, "echo hi", _get_pty=True)

        assert connection.processes[-1].term_type == "vt100"

    async def test_run_shell_command_output(self):
        _, host, connection = await self.connect_host()
        connection.add_response(0, stdout=["out1", "", "out2"], stderr=["err1"])

        status, output = await async_def(host.run_shell_command, "echo hi")

        assert status is True
        # Empty lines are kept, the EOF chunk is not
        assert output.stdout_lines == ["out1", "", "out2"]
        assert output.stderr_lines == ["err1"]

    @mock.patch("pyinfra.api.output._echo")
    async def test_run_shell_command_masked(self, fake_echo):
        _, host, connection = await self.connect_host()

        command = StringCommand("echo", HiddenValue("top-secret-stuff"))

        status, output = await async_def(
            host.run_shell_command, command, print_output=True, print_input=True
        )
        assert status is True

        assert connection.commands[-1] == "sh -c 'echo top-secret-stuff'"

        fake_echo.assert_called_with(
            f"{host.print_prefix}>>> sh -c 'echo *MASKED*'",
            err=True,
        )

    async def test_run_shell_command_success_exit_code(self):
        _, host, connection = await self.connect_host()
        connection.add_response(1)

        status, _ = await async_def(host.run_shell_command, "echo hi", _success_exit_codes=[1])
        assert status is True

    async def test_run_shell_command_error(self):
        _, host, connection = await self.connect_host()
        connection.add_response(1)

        status, _ = await async_def(host.run_shell_command, "echo hi")
        assert status is False

    async def test_run_shell_command_timeout(self):
        _, host, connection = await self.connect_host()
        connection.add_response(0, delay=10)

        with self.assertRaises(TimeoutError):
            await async_def(host.run_shell_command, "sleep 10", _timeout=0.01)

        assert connection.processes[-1].closed is True

    async def _test_sudo_password_prompt(self, password, expected_env):
        _, host, connection = await self.connect_host()

        connection.add_response(1, stdout=["sudo: a password is required\r"])
        connection.add_response(0, stdout=["/tmp/pyinfra-sudo-askpass-XXXXXXXXXXXX"])
        connection.add_response(0)

        with mock.patch("pyinfra.connectors.util.getpass", return_value=password):
            status, _ = await async_def(
                host.run_shell_command, "echo Šablony", _sudo=True, print_output=True
            )

        assert status is True
        assert len(connection.commands) == 3
        assert connection.commands[0] == "sudo -H -n sh -c 'echo Šablony'"
        assert connection.commands[-1] == (
            f"env SUDO_ASKPASS=/tmp/pyinfra-sudo-askpass-XXXXXXXXXXXX {expected_env} "
            "sudo -H -A -k sh -c 'echo Šablony'"
        )

    async def test_run_shell_command_sudo_password_automatic_prompt(self):
        await self._test_sudo_password_prompt("password", "PYINFRA_SUDO_PASSWORD=password")

    async def test_run_shell_command_sudo_password_automatic_prompt_with_special_chars(self):
        await self._test_sudo_password_prompt(
            "p@ss'word';",
            """PYINFRA_SUDO_PASSWORD='p@ss'"'"'word'"'"';'""",
        )

    async def _test_sudo_password_retry(self, prompt_line):
        _, host, connection = await self.connect_host()
        host.connector_data["sudo_askpass_path__/tmp"] = "/tmp/pyinfra-sudo-askpass-XXXXXXXXXXXX"

        connection.add_response(1, stderr=[prompt_line])
        connection.add_response(0)

        with mock.patch("pyinfra.connectors.util.getpass", return_value="PASSWORD") as getpass:
            status, _ = await async_def(host.run_shell_command, "echo hi", _sudo=True)

        assert status is True
        assert getpass.called
        assert connection.commands[-1] == (
            "env SUDO_ASKPASS=/tmp/pyinfra-sudo-askpass-XXXXXXXXXXXX "
            "PYINFRA_SUDO_PASSWORD=PASSWORD sudo -H -A -k sh -c 'echo hi'"
        )

    async def test_run_shell_command_retry_for_sudo_password(self):
        await self._test_sudo_password_retry("sudo: a password is required")

    async def test_run_shell_command_retry_for_sudo_rs_password(self):
        # sudo-rs (the Rust replacement, default in Ubuntu 25.10+) prints a different message
        # when it cannot prompt non-interactively; the retry path should recognize it too.
        await self._test_sudo_password_retry("sudo-rs: interactive authentication is required")

    # SSH file put/get tests
    #

    async def test_put_file(self):
        state, host, connection = await self.connect_host(hosts=("anotherhost",))

        fake_open = mock.mock_open(read_data="test!")
        with mock.patch("pyinfra.api.util.open", fake_open, create=True):
            with ctx_state.use(state):
                status = await async_def(
                    host.put_file, "not-a-file", "not-another-file", print_output=True
                )

        assert status is True
        assert connection.sftp.opened == [("not-another-file", "wb")]
        assert connection.sftp.written == {"not-another-file": [b"test!"]}

    async def test_put_file_sudo(self):
        state, host, connection = await self.connect_host(hosts=("anotherhost",))

        fake_open = mock.mock_open(read_data="test!")
        with mock.patch("pyinfra.api.util.open", fake_open, create=True):
            with ctx_state.use(state):
                status = await async_def(
                    host.put_file,
                    "not-a-file",
                    "not another file",
                    print_output=True,
                    _sudo=True,
                    _sudo_user="ubuntu",
                )

        assert status is True

        temp_file = "/tmp/pyinfra-de01e82cb691e8a31369da3c7c8f17341c44ac24"
        assert connection.sftp.opened == [(temp_file, "wb")]
        assert connection.commands == [
            f"sh -c 'setfacl -m u:ubuntu:r {temp_file}'",
            f"sudo -H -n -u ubuntu sh -c 'cp {temp_file} '\"'\"'not another file'\"'\"''",
            f"sh -c 'rm -f {temp_file}'",
        ]

    async def test_put_file_doas(self):
        state, host, connection = await self.connect_host(hosts=("anotherhost",))

        fake_open = mock.mock_open(read_data="test!")
        with mock.patch("pyinfra.api.util.open", fake_open, create=True):
            with ctx_state.use(state):
                status = await async_def(
                    host.put_file,
                    "not-a-file",
                    "not another file",
                    print_output=True,
                    _doas=True,
                    _doas_user="ubuntu",
                )

        assert status is True

        temp_file = "/tmp/pyinfra-de01e82cb691e8a31369da3c7c8f17341c44ac24"
        assert connection.commands == [
            f"sh -c 'setfacl -m u:ubuntu:r {temp_file}'",
            f"doas -n -u ubuntu sh -c 'cp {temp_file} '\"'\"'not another file'\"'\"''",
            f"sh -c 'rm -f {temp_file}'",
        ]

    async def test_put_file_su_user_fail_acl(self):
        state, host, connection = await self.connect_host(hosts=("anotherhost",))
        connection.add_response(1)

        fake_open = mock.mock_open(read_data="test!")
        with mock.patch("pyinfra.api.util.open", fake_open, create=True):
            with ctx_state.use(state):
                status = await async_def(
                    host.put_file,
                    "not-a-file",
                    "not-another-file",
                    print_output=True,
                    _su_user="centos",
                )

        assert status is False
        assert connection.commands == [
            "sh -c 'setfacl -m u:centos:r /tmp/pyinfra-43db9984686317089fefcf2e38de527e4cb44487'",
        ]

    async def test_put_file_su_user_fail_copy(self):
        state, host, connection = await self.connect_host(hosts=("anotherhost",))
        assert isinstance(host, Host)

        connection.add_response(0)
        connection.add_response(1)

        fake_open = mock.mock_open(read_data="test!")
        with mock.patch("pyinfra.api.util.open", fake_open, create=True):
            with ctx_state.use(state):
                status = await async_def(
                    host.put_file,
                    fake_open(),
                    "not-another-file",
                    print_output=True,
                    _su_user="centos",
                )

        assert status is False
        assert connection.commands == [
            "sh -c 'setfacl -m u:centos:r /tmp/pyinfra-43db9984686317089fefcf2e38de527e4cb44487'",
            (
                "su centos -c 'sh -c '\"'\"'cp "
                "/tmp/pyinfra-43db9984686317089fefcf2e38de527e4cb44487 "
                "not-another-file'\"'\"''"
            ),
        ]

    async def test_put_file_sudo_custom_temp_file(self):
        state, host, connection = await self.connect_host(hosts=("anotherhost",))

        fake_open = mock.mock_open(read_data="test!")
        with mock.patch("pyinfra.api.util.open", fake_open, create=True):
            with ctx_state.use(state):
                status = await async_def(
                    host.put_file,
                    "not-a-file",
                    "not another file",
                    print_output=True,
                    _sudo=True,
                    _sudo_user="ubuntu",
                    remote_temp_filename="/a-different-tempfile",
                )

        assert status is True
        assert connection.sftp.opened == [("/a-different-tempfile", "wb")]
        assert connection.commands[-1] == "sh -c 'rm -f /a-different-tempfile'"

    async def test_put_file_retries_transfer_errors(self):
        state, host, connection = await self.connect_host(hosts=("anotherhost",))

        errors = [asyncssh.SFTPError(4, "failure"), OSError("boom")]

        original_open = connection.sftp.open

        def flaky_open(path, mode):
            if errors:
                raise errors.pop(0)
            return original_open(path, mode)

        fake_open = mock.mock_open(read_data="test!")
        with (
            mock.patch("pyinfra.api.util.open", fake_open, create=True),
            mock.patch.object(connection.sftp, "open", flaky_open),
        ):
            with ctx_state.use(state):
                status = await async_def(host.put_file, "not-a-file", "not-another-file")

        assert status is True
        assert connection.sftp.written == {"not-another-file": [b"test!"]}

    async def test_get_file(self):
        state, host, connection = await self.connect_host()
        connection.sftp.read_data = [b"test!"]

        fake_open = mock.mock_open()
        with mock.patch("pyinfra.api.util.open", fake_open, create=True):
            with ctx_state.use(state):
                status = await async_def(
                    host.get_file, "not-a-file", "not-another-file", print_output=True
                )

        assert status is True
        assert connection.sftp.opened == [("not-a-file", "rb")]
        fake_open.assert_called_with("not-another-file", "wb")
        fake_open().write.assert_called_with(b"test!")

    async def test_get_file_failure_leaves_local_file_alone(self):
        state, host, connection = await self.connect_host()
        connection.sftp.open_side_effect = PermissionError(13, "Permission denied")

        with TemporaryDirectory() as temp_dir:
            local_file = Path(temp_dir) / "existing-file"
            local_file.write_bytes(b"do not truncate me")

            with ctx_state.use(state):
                with self.assertRaises(PermissionError):
                    await async_def(host.get_file, "not-a-file", str(local_file))

            assert local_file.read_bytes() == b"do not truncate me"

    async def test_get_file_sudo(self):
        state, host, connection = await self.connect_host()

        fake_open = mock.mock_open()
        with mock.patch("pyinfra.api.util.open", fake_open, create=True):
            with ctx_state.use(state):
                status = await async_def(
                    host.get_file,
                    "not-a-file",
                    "not-another-file",
                    print_output=True,
                    _sudo=True,
                    _sudo_user="ubuntu",
                )

        assert status is True

        temp_file = "/tmp/pyinfra-e9c0d3c8ffca943daa0e75511b0a09c84b59c508"
        assert connection.sftp.opened == [(temp_file, "rb")]
        assert connection.commands == [
            f"sudo -H -n -u ubuntu sh -c 'cp not-a-file {temp_file} && chmod +r {temp_file}'",
            f"sudo -H -n -u ubuntu sh -c 'rm -f {temp_file}'",
        ]

    async def test_get_file_sudo_copy_fail(self):
        state, host, connection = await self.connect_host()
        connection.add_response(1)

        with ctx_state.use(state):
            status = await async_def(
                host.get_file,
                "not-a-file",
                "not-another-file",
                print_output=True,
                _sudo=True,
                _sudo_user="ubuntu",
            )

        assert status is False

        temp_file = "/tmp/pyinfra-e9c0d3c8ffca943daa0e75511b0a09c84b59c508"
        assert connection.sftp.opened == []
        assert connection.commands == [
            f"sudo -H -n -u ubuntu sh -c 'cp not-a-file {temp_file} && chmod +r {temp_file}'",
        ]

    async def test_get_file_sudo_remove_fail(self):
        state, host, connection = await self.connect_host()
        connection.add_response(0)
        connection.add_response(1)

        fake_open = mock.mock_open()
        with mock.patch("pyinfra.api.util.open", fake_open, create=True):
            with ctx_state.use(state):
                status = await async_def(
                    host.get_file,
                    "not-a-file",
                    "not-another-file",
                    print_output=True,
                    _sudo=True,
                    _sudo_user="ubuntu",
                )

        assert status is False

        temp_file = "/tmp/pyinfra-e9c0d3c8ffca943daa0e75511b0a09c84b59c508"
        assert connection.commands == [
            f"sudo -H -n -u ubuntu sh -c 'cp not-a-file {temp_file} && chmod +r {temp_file}'",
            f"sudo -H -n -u ubuntu sh -c 'rm -f {temp_file}'",
        ]

    async def test_get_file_su_user(self):
        state, host, connection = await self.connect_host()

        fake_open = mock.mock_open()
        with mock.patch("pyinfra.api.util.open", fake_open, create=True):
            with ctx_state.use(state):
                status = await async_def(
                    host.get_file,
                    "not-a-file",
                    "not-another-file",
                    print_output=True,
                    _su_user="centos",
                )

        assert status is True

        temp_file = "/tmp/pyinfra-e9c0d3c8ffca943daa0e75511b0a09c84b59c508"
        assert connection.commands == [
            (
                "su centos -c 'sh -c '\"'\"'cp not-a-file "
                f"{temp_file} && chmod +r "
                f"{temp_file}'\"'\"''"
            ),
            f"su centos -c 'sh -c '\"'\"'rm -f {temp_file}'\"'\"''",
        ]

    async def test_get_sftp_fail(self):
        state, host, connection = await self.connect_host(hosts=("anotherhost",))

        connection.sftp_side_effect = asyncssh.Error(1, "no sftp for you")

        fake_open = mock.mock_open(read_data="test!")
        with mock.patch("pyinfra.api.util.open", fake_open, create=True):
            with ctx_state.use(state):
                with self.assertRaises(ConnectError):
                    await async_def(host.put_file, "not-a-file", "not-another-file")

    async def test_scp_transfer(self):
        state, host, connection = await self.connect_host(
            {"ssh_file_transfer_protocol": "scp"},
        )

        fake_open = mock.mock_open(read_data="test!")
        with (
            mock.patch("pyinfra.api.util.open", fake_open, create=True),
            mock.patch("pyinfra.connectors.ssh.asyncssh.scp", new=mock.AsyncMock()) as fake_scp,
        ):
            with ctx_state.use(state):
                status = await async_def(host.put_file, "not-a-file", "not-another-file")

        assert status is True
        fake_scp.assert_called_once()
        (local_path, (scp_connection, remote_path)), _ = fake_scp.call_args
        assert scp_connection is connection
        assert remote_path == "not-another-file"
        assert connection.sftp.opened == []

    async def test_invalid_file_transfer_protocol(self):
        state, host, connection = await self.connect_host(
            {"ssh_file_transfer_protocol": "carrier-pigeon"},
        )

        fake_open = mock.mock_open(read_data="test!")
        with mock.patch("pyinfra.api.util.open", fake_open, create=True):
            with ctx_state.use(state):
                with self.assertRaises(ConnectError):
                    await async_def(host.put_file, "not-a-file", "not-another-file")
