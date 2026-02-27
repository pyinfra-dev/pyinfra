from __future__ import annotations

import asyncio
import os
import random
import shlex
import tempfile
import warnings
from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    Iterable,
    Optional,
    Protocol,
    cast,
)

from socket import timeout as timeout_error

import asyncssh
import click
import pyinfra
from typing_extensions import TypedDict, Unpack, override

from pyinfra import logger
from pyinfra.api.command import StringCommand
from pyinfra.api.exceptions import ConnectError, PyinfraError
from pyinfra.api.util import get_file_io, memoize

from .base import BaseConnector, DataMeta
from .util import (
    CommandOutput,
    OutputLine,
    async_make_unix_command_for_host,
    execute_command_with_sudo_retry_async,
    run_local_process_async,
)

if TYPE_CHECKING:
    from pyinfra.api.arguments import ConnectorArguments
    from pyinfra.api.host import Host
    from pyinfra.api.state import State


class ConnectorData(TypedDict):
    ssh_hostname: str
    ssh_port: int
    ssh_user: str
    ssh_password: str
    ssh_key: str
    ssh_key_password: str

    ssh_allow_agent: bool
    ssh_look_for_keys: bool
    ssh_forward_agent: bool

    ssh_config_file: str
    ssh_known_hosts_file: str
    ssh_strict_host_key_checking: str

    ssh_paramiko_connect_kwargs: dict  # backward compatibility name

    ssh_connect_retries: int
    ssh_connect_retry_min_delay: float
    ssh_connect_retry_max_delay: float
    ssh_file_transfer_protocol: str


connector_data_meta: dict[str, DataMeta] = {
    "ssh_hostname": DataMeta("SSH hostname"),
    "ssh_port": DataMeta("SSH port"),
    "ssh_user": DataMeta("SSH user"),
    "ssh_password": DataMeta("SSH password"),
    "ssh_key": DataMeta("SSH key filename"),
    "ssh_key_password": DataMeta("SSH key password"),
    "ssh_allow_agent": DataMeta("Whether to use any active SSH agent", True),
    "ssh_look_for_keys": DataMeta("Whether to look for private keys", True),
    "ssh_forward_agent": DataMeta("Whether to enable SSH forward agent", False),
    "ssh_config_file": DataMeta("SSH config filename"),
    "ssh_known_hosts_file": DataMeta("SSH known_hosts filename"),
    "ssh_strict_host_key_checking": DataMeta(
        "SSH strict host key checking",
        "accept-new",
    ),
    "ssh_paramiko_connect_kwargs": DataMeta(
        "Override keyword arguments passed into asyncssh.connect",
    ),
    "ssh_connect_retries": DataMeta("Number of tries to connect via ssh", 0),
    "ssh_connect_retry_min_delay": DataMeta(
        "Lower bound for random delay between retries",
        0.1,
    ),
    "ssh_connect_retry_max_delay": DataMeta(
        "Upper bound for random delay between retries",
        0.5,
    ),
    "ssh_file_transfer_protocol": DataMeta(
        "Protocol to use for file transfers. Can be ``sftp``.",
        "sftp",
    ),
}


class FileTransferClient(Protocol):
    def getfo(self, remote_filename: str, fl: IO) -> Any | None: ...

    def putfo(self, fl: IO, remote_filename: str) -> Any | None: ...


def _expand_user_path(path: str | None) -> str | None:
    if not path:
        return None

    if path.startswith("~/"):
        home = os.environ.get("HOME")
        if home:
            return os.path.normpath(os.path.join(home, path[2:]))

    return os.path.expanduser(path)


def _format_known_host(hostname: str, port: Optional[int]) -> str:
    if port and port != 22:
        return f"[{hostname}]:{port}"
    return hostname


def _normalise_stdin(stdin: Any) -> Optional[str]:
    if stdin is None:
        return None
    if isinstance(stdin, (bytes, str)):
        return stdin.decode() if isinstance(stdin, bytes) else stdin
    if isinstance(stdin, Iterable):
        return "".join(str(item) for item in stdin)
    return str(stdin)


class _SFTPWrapper:
    def __init__(self, connector: "SSHConnector") -> None:
        self._connector = connector

    def getfo(self, remote_filename: str, fl: IO) -> None:
        data = self._connector.host._run_async(self._connector._async_read_file(remote_filename))
        fl.write(data)

    def putfo(self, fl: IO, remote_filename: str) -> None:
        position = fl.tell()
        fl.seek(0)
        data = fl.read()
        fl.seek(position)
        if isinstance(data, str):
            data = data.encode()
        self._connector.host._run_async(self._connector._async_write_file(remote_filename, data))


class _SCPWrapper:
    def __init__(self, connector: "SSHConnector") -> None:
        self._connector = connector

    def getfo(self, remote_filename: str, fl: IO) -> None:
        data = self._connector.host._run_async(self._connector._async_scp_download(remote_filename))
        fl.write(data)

    def putfo(self, fl: IO, remote_filename: str) -> None:
        position = fl.tell() if hasattr(fl, "tell") else None
        if hasattr(fl, "seek"):
            fl.seek(0)
        data = fl.read()
        if position is not None and hasattr(fl, "seek"):
            fl.seek(position)
        if isinstance(data, str):
            data = data.encode()
        self._connector.host._run_async(self._connector._async_scp_upload(remote_filename, data))


class SSHConnector(BaseConnector):
    handles_execution = True

    data_cls = ConnectorData
    data_meta = connector_data_meta
    data: ConnectorData

    def __init__(self, state: "State", host: "Host"):
        super().__init__(state, host)
        self._connection: asyncssh.SSHClientConnection | None = None
        self._sftp_client: asyncssh.SFTPClient | None = None
        self._known_hosts_file: str | None = None
        self._strict_host_key_checking: str = (
            self.data["ssh_strict_host_key_checking"] or "accept-new"
        )
        self._transfer_protocol = (self.data.get("ssh_file_transfer_protocol") or "sftp").lower()
        self._strict_setting: str = self._strict_host_key_checking.lower()

    @override
    @staticmethod
    def make_names_data(name):
        yield f"@ssh/{name}", {"ssh_hostname": name}, []

    # Connection management

    def _build_connect_kwargs(
        self,
        hostname: str,
        strict_setting: str,
    ) -> tuple[str, dict[str, Any]]:
        kwargs: dict[str, Any] = {
            "username": self.data["ssh_user"] or None,
            "port": int(self.data["ssh_port"]) if self.data["ssh_port"] else None,
            "password": self.data["ssh_password"] or None,
            "agent_forwarding": self.data["ssh_forward_agent"],
            "login_timeout": self.state.config.CONNECT_TIMEOUT,
        }

        ssh_key = self.data["ssh_key"]
        ssh_key_password = self.data["ssh_key_password"]

        if ssh_key:
            key, certs = self._load_private_key(ssh_key, ssh_key_password)
            kwargs["client_keys"] = [key]
            if certs:
                kwargs.setdefault("client_certs", []).extend(certs)
        elif not self.data["ssh_look_for_keys"]:
            kwargs["client_keys"] = []

        if not self.data["ssh_allow_agent"]:
            kwargs["agent_path"] = ()

        read_config = getattr(asyncssh, "read_ssh_config", None)
        config_files: list[str] = []

        ssh_config_file = self.data["ssh_config_file"]
        if ssh_config_file:
            expanded_config = _expand_user_path(ssh_config_file)
            config_files.append(expanded_config or ssh_config_file)
        else:
            default_config = _expand_user_path("~/.ssh/config")
            if default_config and os.path.isfile(default_config):
                config_files.append(default_config)

        if config_files:
            if read_config is None:
                if ssh_config_file:
                    raise ConnectError("AsyncSSH does not provide read_ssh_config support")
            else:
                parsed_configs = []
                for config_file in config_files:
                    try:
                        parsed_configs.append(read_config(config_file))
                    except FileNotFoundError:
                        if ssh_config_file:
                            raise ConnectError(
                                f"SSH config file not found: {config_file}"
                            ) from None
                if parsed_configs:
                    kwargs["config"] = (
                        parsed_configs[0] if len(parsed_configs) == 1 else parsed_configs
                    )

        known_hosts_data = self.data.get("ssh_known_hosts_file") or None
        if known_hosts_data:
            known_hosts_path = _expand_user_path(known_hosts_data)
            if known_hosts_path is None:
                known_hosts_path = known_hosts_data
        else:
            known_hosts_path = _expand_user_path("~/.ssh/known_hosts")

        self._known_hosts_file = known_hosts_path if known_hosts_path else None

        if strict_setting in {"no", "off"}:
            kwargs["known_hosts"] = None
        elif strict_setting == "yes":
            if self._known_hosts_file:
                kwargs["known_hosts"] = self._known_hosts_file
        else:
            kwargs["known_hosts"] = None

        extra_kwargs = self.data.get("ssh_paramiko_connect_kwargs") or {}
        converted_kwargs, hostname_override = self._convert_paramiko_kwargs(extra_kwargs, kwargs)
        if hostname_override:
            hostname = hostname_override
        kwargs.update(converted_kwargs)

        if kwargs.get("port") is None:
            kwargs.pop("port")

        return hostname, kwargs

    def _convert_paramiko_kwargs(
        self,
        paramiko_kwargs: dict[str, Any],
        base_kwargs: dict[str, Any],
    ) -> tuple[dict[str, Any], str | None]:
        if not paramiko_kwargs:
            return {}, None

        warnings.warn(
            "ssh_paramiko_connect_kwargs is deprecated and will be removed in a future release. "
            "Update host data to use AsyncSSH options directly.",
            DeprecationWarning,
            stacklevel=4,
        )

        converted: dict[str, Any] = {}
        hostname_override: str | None = None

        passphrase = paramiko_kwargs.get("passphrase")

        handled_keys = {
            "hostname",
            "username",
            "port",
            "password",
            "timeout",
            "auth_timeout",
            "banner_timeout",
            "allow_agent",
            "look_for_keys",
            "compress",
            "key_filename",
            "pkey",
        }

        for key in handled_keys:
            if key not in paramiko_kwargs:
                continue

            value = paramiko_kwargs[key]

            if key == "hostname" and value:
                hostname_override = str(value)
                continue

            if key == "username" and value:
                converted["username"] = value
                continue

            if key == "port" and value:
                converted["port"] = int(value)
                continue

            if key == "password" and value is not None:
                converted["password"] = value
                continue

            if key == "timeout" and value:
                converted["connect_timeout"] = value
                continue

            if key == "auth_timeout" and value:
                converted["login_timeout"] = value
                continue

            if key == "banner_timeout" and value:
                converted["banner_timeout"] = value
                continue

            if key == "allow_agent":
                if not value:
                    converted["agent_path"] = ()
                continue

            if key == "look_for_keys":
                if (
                    not value
                    and "client_keys" not in base_kwargs
                    and "client_keys" not in converted
                ):
                    converted["client_keys"] = []
                continue

            if key == "compress":
                if value:
                    converted["compression_algs"] = ["zlib@openssh.com", "zlib"]
                else:
                    converted["compression_algs"] = ["none"]
                continue

            if key == "key_filename" and value:
                filenames: Iterable[str]
                if isinstance(value, (list, tuple, set)):
                    filenames = [str(item) for item in value]
                else:
                    filenames = [str(value)]

                keys: list[asyncssh.SSHKey] = []
                certs: list[asyncssh.SSHKey] = []
                for filename in filenames:
                    key_obj, key_certs = self._load_private_key(
                        filename,
                        passphrase or self.data["ssh_key_password"],
                    )
                    keys.append(key_obj)
                    certs.extend(key_certs)

                converted["client_keys"] = keys
                if certs:
                    converted.setdefault("client_certs", []).extend(certs)
                continue

            if key == "pkey" and value is not None:
                logger.warning(
                    "Ignoring Paramiko private key object provided via ssh_paramiko_connect_kwargs; "
                    "specify ssh_key or ssh_paramiko_connect_kwargs['key_filename'] instead.",
                )
                continue

        passthrough = {
            key: value
            for key, value in paramiko_kwargs.items()
            if key not in handled_keys and not key.startswith("_pyinfra_")
        }

        converted.update(passthrough)

        return converted, hostname_override

    def _load_private_key(
        self,
        key_filename: str,
        key_password: str,
    ) -> tuple[asyncssh.SSHKey, list[asyncssh.SSHKey]]:
        if key_filename in self.state.private_keys:
            key = self.state.private_keys[key_filename]
            certs = self.state.private_key_certs.get(key_filename, [])
            return key, certs

        candidate_paths = []
        if self.state.cwd:
            candidate_paths.append(os.path.join(self.state.cwd, key_filename))
        candidate_paths.append(os.path.expanduser(key_filename))

        for filename in candidate_paths:
            if not os.path.isfile(filename):
                continue

            passphrase = key_password

            while True:
                try:
                    key = asyncssh.read_private_key(filename, passphrase=passphrase)
                    certs = self._load_private_key_certificates(filename)
                    self.state.private_keys[key_filename] = key
                    self.state.private_key_certs[key_filename] = certs
                    return key, certs
                except asyncssh.KeyImportError as exc:  # encrypted key without passphrase
                    if "encrypted" not in str(exc).lower():
                        break

                    if passphrase:
                        break

                    if pyinfra.is_cli:
                        passphrase = click.prompt(
                            f"Enter password for private key: {key_filename}",
                            hide_input=True,
                        )
                    else:
                        raise PyinfraError(
                            "Private key file ({0}) is encrypted, set ssh_key_password to use this key".format(
                                key_filename,
                            ),
                        )

        raise PyinfraError(f"No such private key file: {key_filename}")

    def _load_private_key_certificates(self, key_path: str) -> list[asyncssh.SSHKey]:
        certificates: list[asyncssh.SSHKey] = []

        base_candidates = {key_path}
        stem, ext = os.path.splitext(key_path)
        if stem:
            base_candidates.add(stem)

        candidate_files: set[str] = set()
        for base in base_candidates:
            for suffix in ("-cert.pub", ".pub"):
                candidate_files.add(f"{base}{suffix}")

        for candidate in candidate_files:
            if not os.path.isfile(candidate):
                continue

            try:
                certificates.append(asyncssh.read_public_key(candidate))
            except (asyncssh.KeyImportError, OSError) as exc:
                logger.warning("Failed to load certificate %s: %s", candidate, exc)

        return certificates

    @override
    async def connect(self) -> None:
        hostname = self.data["ssh_hostname"] or self.host.name
        if self._transfer_protocol not in {"sftp", "scp"}:
            raise ConnectError(f"Unsupported file transfer protocol: {self._transfer_protocol}")
        strict_setting = (self.data["ssh_strict_host_key_checking"] or "accept-new").lower()
        self._strict_setting = strict_setting
        hostname, kwargs = self._build_connect_kwargs(hostname, strict_setting)
        logger.debug("Connecting to: %s (%r)", hostname, kwargs)

        try:
            self._connection = await self._async_connect(hostname, kwargs, strict_setting)
        except (asyncssh.Error, OSError) as exc:
            raise ConnectError(f"SSH error connecting to {hostname}: {exc}")

    async def _async_connect(
        self,
        hostname: str,
        kwargs: dict[str, Any],
        strict_setting: str,
    ) -> asyncssh.SSHClientConnection:
        retries = self.data["ssh_connect_retries"]
        delay_min = self.data["ssh_connect_retry_min_delay"]
        delay_max = self.data["ssh_connect_retry_max_delay"]

        attempt = 0
        while True:
            try:
                connection = await asyncssh.connect(hostname, **kwargs)
                await self._handle_host_key_policy(
                    connection, hostname, kwargs.get("port"), strict_setting
                )
                return connection
            except (asyncssh.Error, OSError):
                attempt += 1
                if attempt > retries:
                    raise
                await asyncio.sleep(random.uniform(delay_min, delay_max))

    async def _store_host_key(
        self,
        connection: asyncssh.SSHClientConnection,
        hostname: str,
        port: Optional[int],
    ) -> None:
        if not self._known_hosts_file:
            return

        host_key = connection.get_server_host_key()
        if host_key is None:
            return

        entry_host = _format_known_host(hostname, port)
        export = host_key.export_public_key()
        export_text = export.decode() if isinstance(export, bytes) else str(export)
        line = f"{entry_host} {export_text}\n"

        directory = os.path.dirname(self._known_hosts_file)
        if directory:
            os.makedirs(directory, exist_ok=True)

        try:
            with open(self._known_hosts_file, "a", encoding="utf-8") as known_hosts:
                known_hosts.write(line)
        except OSError as exc:
            logger.warning("Failed to write host key for %s: %s", entry_host, exc)

    def _load_known_host_keys(self, hostname: str, port: Optional[int]) -> list[asyncssh.SSHKey]:
        if not self._known_hosts_file:
            return []

        if not os.path.exists(self._known_hosts_file):
            return []

        try:
            known_hosts = asyncssh.read_known_hosts(self._known_hosts_file)
        except (OSError, asyncssh.Error) as exc:
            logger.warning("Failed to read known_hosts file %s: %s", self._known_hosts_file, exc)
            return []

        matches = known_hosts.match(hostname, "", port)
        matched_keys: list[asyncssh.SSHKey] = []
        for key_group in matches[:3]:
            matched_keys.extend(key_group)
        return matched_keys

    @staticmethod
    def _host_keys_equal(existing_key: asyncssh.SSHKey, host_key: asyncssh.SSHKey) -> bool:
        return existing_key.export_public_key() == host_key.export_public_key()

    async def _handle_host_key_policy(
        self,
        connection: asyncssh.SSHClientConnection,
        hostname: str,
        port: Optional[int],
        strict_setting: str,
    ) -> None:
        strict = (strict_setting or "accept-new").lower()

        if strict in {"no", "off"}:
            return

        host_key = connection.get_server_host_key()
        if host_key is None:
            return

        existing_keys = self._load_known_host_keys(hostname, port)

        if existing_keys:
            if any(self._host_keys_equal(key, host_key) for key in existing_keys):
                return

            connection.close()
            await connection.wait_closed()
            raise ConnectError("SSH host key mismatch detected; refusing connection.")

        if strict == "yes":
            connection.close()
            await connection.wait_closed()
            raise ConnectError(
                "SSH host key not found in known_hosts and strict checking is enabled."
            )

        if strict == "ask":
            if not pyinfra.is_cli:
                connection.close()
                await connection.wait_closed()
                raise ConnectError(
                    "SSH host key not found in known_hosts and interactive confirmation is unavailable."
                )

            message = f"No host key for {hostname} found in known_hosts. Do you want to accept and add it?"
            if not click.confirm(message, default=False):
                connection.close()
                await connection.wait_closed()
                raise ConnectError("User declined to accept new SSH host key.")

        await self._store_host_key(connection, hostname, port)

    @override
    async def disconnect(self) -> None:
        if self._sftp_client:
            self._sftp_client.exit()
            self._sftp_client = None

        if self._connection is not None:
            self._connection.close()
            await self._connection.wait_closed()
            self._connection = None

    # Command execution

    @override
    async def run_shell_command(
        self,
        command: StringCommand,
        print_output: bool = False,
        print_input: bool = False,
        **arguments: Unpack["ConnectorArguments"],
    ) -> tuple[bool, CommandOutput]:
        command_arguments: dict[str, Any] = dict(arguments)

        get_pty = command_arguments.pop("_get_pty", False)
        timeout = command_arguments.pop("_timeout", None)
        stdin_value = command_arguments.pop("_stdin", None)
        success_exit_codes = command_arguments.pop("_success_exit_codes", None)

        async def execute_command() -> tuple[int, CommandOutput]:
            unix_command = await async_make_unix_command_for_host(
                self.state,
                self.host,
                command,
                **command_arguments,
            )
            actual_command = unix_command.get_raw_value()

            logger.debug(
                "Running command on %s: (pty=%s) %s",
                self.host.name,
                get_pty,
                unix_command,
            )

            if print_input:
                click.echo(f"{self.host.print_prefix}>>> {unix_command}", err=True)

            stdin_normalised = _normalise_stdin(stdin_value)

            try:
                exit_status, combined_output = await self._async_run_command(
                    actual_command,
                    stdin_normalised,
                    get_pty,
                    timeout,
                    print_output,
                    self.host.print_prefix,
                )
            except asyncio.TimeoutError as exc:
                raise timeout_error() from exc

            return exit_status, combined_output

        connector_args = cast("ConnectorArguments", command_arguments)

        return_code, combined_output = await execute_command_with_sudo_retry_async(
            self.host,
            connector_args,
            execute_command,
        )

        if success_exit_codes is not None:
            status = return_code in success_exit_codes
        else:
            status = return_code == 0

        return status, combined_output

    async def _async_run_command(
        self,
        command: str,
        stdin_value: Optional[str],
        get_pty: bool,
        timeout: Optional[int],
        print_output: bool,
        print_prefix: str,
    ) -> tuple[int, CommandOutput]:
        assert self._connection is not None, "SSH connection not initialised"

        try:
            result = await self._connection.run(
                command,
                check=False,
                term_type="xterm" if get_pty else None,
                input=stdin_value,
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            raise

        stdout_value = result.stdout or ""
        stderr_value = result.stderr or ""

        if isinstance(stdout_value, bytes):
            stdout_text = stdout_value.decode()
        else:
            stdout_text = stdout_value

        if isinstance(stderr_value, bytes):
            stderr_text = stderr_value.decode()
        else:
            stderr_text = stderr_value

        combined_lines: list[OutputLine] = []

        for line in stdout_text.splitlines():
            if print_output:
                click.echo(f"{print_prefix}{line}", err=True)
            combined_lines.append(OutputLine("stdout", line))

        for line in stderr_text.splitlines():
            if print_output:
                click.echo(f"{print_prefix}{click.style(line, 'red')}", err=True)
            combined_lines.append(OutputLine("stderr", line))

        exit_status = result.exit_status if result.exit_status is not None else 0

        return exit_status, CommandOutput(combined_lines)

    # File transfer helpers

    async def _ensure_sftp(self) -> asyncssh.SFTPClient:
        assert self._connection is not None, "SSH connection not initialised"
        if self._sftp_client is None:
            self._sftp_client = await self._connection.start_sftp_client()
        return self._sftp_client

    async def _async_read_file(self, remote_filename: str) -> bytes:
        sftp = await self._ensure_sftp()
        async with sftp.open(remote_filename, "rb") as remote_file:
            return await remote_file.read()

    async def _async_write_file(self, remote_filename: str, data: bytes) -> None:
        sftp = await self._ensure_sftp()
        async with sftp.open(remote_filename, "wb") as remote_file:
            await remote_file.write(data)

    async def _async_scp_upload(self, remote_filename: str, data: bytes) -> None:
        assert self._connection is not None, "SSH connection not initialised"

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(data)
            temp_file.flush()
            temp_path = temp_file.name

        try:
            await asyncssh.scp(temp_path, (self._connection, remote_filename))
        finally:
            try:
                os.unlink(temp_path)
            except FileNotFoundError:
                pass

    async def _async_scp_download(self, remote_filename: str) -> bytes:
        assert self._connection is not None, "SSH connection not initialised"

        basename = os.path.basename(remote_filename.rstrip("/")) or "pyinfra-download"
        with tempfile.TemporaryDirectory() as temp_dir:
            local_path = os.path.join(temp_dir, basename)
            await asyncssh.scp((self._connection, remote_filename), local_path)
            with open(local_path, "rb") as local_file:
                return local_file.read()

    @memoize
    def get_file_transfer_connection(self) -> FileTransferClient:
        if self._transfer_protocol == "scp":
            return _SCPWrapper(self)
        return _SFTPWrapper(self)

    @override
    async def get_file(
        self,
        remote_filename: str,
        filename_or_io,
        remote_temp_filename=None,
        print_output: bool = False,
        print_input: bool = False,
        **arguments: Unpack["ConnectorArguments"],
    ) -> bool:
        sudo_enabled = arguments.get("_sudo", False)
        su_user = arguments.get("_su_user", None)

        if sudo_enabled or su_user:
            temp_file = remote_temp_filename or self.host.get_temp_filename(remote_filename)
            command = StringCommand(
                "cp",
                remote_filename,
                temp_file,
                "&&",
                "chmod",
                "+r",
                temp_file,
            )

            copy_status, output = await self.run_shell_command(
                command,
                print_output=print_output,
                print_input=print_input,
                **arguments,
            )

            if copy_status is False:
                logger.error("File download copy temp error: %s", output.stderr)
                return False

            try:
                await self._download_file(temp_file, filename_or_io)
            finally:
                await self.run_shell_command(
                    StringCommand("rm", "-f", temp_file),
                    print_output=print_output,
                    print_input=print_input,
                    **arguments,
                )
        else:
            await self._download_file(remote_filename, filename_or_io)

        if print_output:
            click.echo(f"{self.host.print_prefix}file downloaded: {remote_filename}", err=True)

        return True

    async def _download_file(self, remote_filename: str, filename_or_io: str | IO) -> None:
        if self._transfer_protocol == "scp":
            data = await self._async_scp_download(remote_filename)
        else:
            data = await self._async_read_file(remote_filename)

        with get_file_io(filename_or_io, "wb") as file_io:
            file_io.write(data)

    async def _upload_file(self, filename_or_io, remote_location):
        with get_file_io(filename_or_io) as file_io:
            data = file_io.read()
            if isinstance(data, str):
                data = data.encode()
            if self._transfer_protocol == "scp":
                await self._async_scp_upload(remote_location, data)
            else:
                await self._async_write_file(remote_location, data)

    @override
    async def put_file(
        self,
        filename_or_io,
        remote_filename,
        remote_temp_filename=None,
        print_output: bool = False,
        print_input: bool = False,
        **arguments: Unpack["ConnectorArguments"],
    ) -> bool:
        sudo_enabled = arguments.get("_sudo", False)
        sudo_user = arguments.get("_sudo_user", False)
        doas_enabled = arguments.get("_doas", False)
        doas_user = arguments.get("_doas_user", False)
        su_user = arguments.get("_su_user", None)

        if sudo_enabled or doas_enabled or su_user:
            temp_file = remote_temp_filename or self.host.get_temp_filename(remote_filename)
            await self._upload_file(filename_or_io, temp_file)

            other_user = su_user or sudo_user or doas_user
            if other_user:
                status, output = await self.run_shell_command(
                    StringCommand("setfacl", "-m", f"u:{other_user}:r", temp_file),
                    print_output=print_output,
                    print_input=print_input,
                    **arguments,
                )
                if status is False:
                    logger.error("Unable to set ACL for temp file: %s", output.stderr)
                    return False

            command = StringCommand(
                "mv",
                temp_file,
                remote_filename,
                "&&",
                "chmod",
                "0644",
                remote_filename,
            )

            status, output = await self.run_shell_command(
                command,
                print_output=print_output,
                print_input=print_input,
                **arguments,
            )

            if status is False:
                logger.error("File upload error: %s", output.stderr)
                return False

        else:
            await self._upload_file(filename_or_io, remote_filename)

        if print_output:
            click.echo(f"{self.host.print_prefix}file uploaded: {remote_filename}", err=True)

        return True

    # Rsync support remains shell-based

    @override
    def check_can_rsync(self) -> None:
        if self.data["ssh_key_password"]:
            raise NotImplementedError(
                "Rsync does not currently work with SSH keys needing passwords."
            )

        if self.data["ssh_password"]:
            raise NotImplementedError("Rsync does not currently work with SSH passwords.")

        from shutil import which

        if not which("rsync"):
            raise NotImplementedError("The `rsync` binary is not available on this system.")

    @override
    async def rsync(
        self,
        src: str,
        dest: str,
        flags: Iterable[str],
        print_output: bool = False,
        print_input: bool = False,
        **arguments: Unpack["ConnectorArguments"],
    ) -> bool:
        arguments_dict = dict(arguments)
        sudo_enabled = arguments_dict.pop("_sudo", False)
        sudo_user = arguments_dict.pop("_sudo_user", False)

        hostname = self.data["ssh_hostname"] or self.host.name
        user = self.data["ssh_user"]
        user_prefix = f"{user}@" if user else ""

        ssh_flags = ["-o BatchMode=yes"]

        if self._known_hosts_file:
            ssh_flags.append(f'-o "UserKnownHostsFile={shlex.quote(self._known_hosts_file)}"')

        strict_setting = (self._strict_host_key_checking or "accept-new").lower()
        ssh_flags.append(f'-o "StrictHostKeyChecking={shlex.quote(strict_setting)}"')

        ssh_config_file = self.data["ssh_config_file"]
        if ssh_config_file:
            ssh_flags.append(f"-F {shlex.quote(ssh_config_file)}")

        port = self.data["ssh_port"]
        if port:
            ssh_flags.append(f"-p {port}")

        ssh_key = self.data["ssh_key"]
        if ssh_key:
            ssh_flags.append(f"-i {shlex.quote(ssh_key)}")

        remote_rsync_command = "rsync"
        if sudo_enabled:
            remote_rsync_command = "sudo rsync"
            if sudo_user:
                remote_rsync_command = f"sudo -u {sudo_user} rsync"

        rsync_command = (
            "rsync {rsync_flags} --rsh \"ssh {ssh_flags}\" --rsync-path '{remote_rsync_command}' "
            "{src} {user_prefix}{hostname}:{dest}"
        ).format(
            rsync_flags=" ".join(flags),
            ssh_flags=" ".join(ssh_flags),
            remote_rsync_command=remote_rsync_command,
            src=src,
            user_prefix=user_prefix,
            hostname=hostname,
            dest=dest,
        )

        if print_input:
            click.echo(f"{self.host.print_prefix}>>> {rsync_command}", err=True)

        return_code, output = await run_local_process_async(
            rsync_command,
            print_output=print_output,
            print_prefix=self.host.print_prefix,
        )

        if return_code != 0:
            raise IOError(output.stderr)

        return True
