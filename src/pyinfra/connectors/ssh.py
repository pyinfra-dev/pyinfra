from __future__ import annotations

import asyncio
import os
from random import uniform
from shutil import copyfileobj, which
from socket import gaierror
from tempfile import NamedTemporaryFile, SpooledTemporaryFile
from typing import IO, TYPE_CHECKING, Any, Protocol
from collections.abc import Iterable

import asyncssh
from typing_extensions import TypedDict, Unpack, override

from pyinfra import logger
from pyinfra.api.concurrency import awaitlet
from pyinfra.api.output import echo
from pyinfra.api.command import QuoteString, StringCommand
from pyinfra.api.exceptions import ConnectError
from pyinfra.api.util import get_file_io

from .base import BaseConnector, DataMeta
from .ssh_hostkeys import PyinfraSSHClient, get_host_key_policy, resolve_known_hosts_files
from .ssh_util import get_private_key, raise_connect_error
from .util import (
    CommandOutput,
    execute_command_with_sudo_retry,
    make_unix_command_for_host,
    read_output_buffers,
    run_local_process,
    write_stdin,
)

if TYPE_CHECKING:
    from pyinfra.api.arguments import ConnectorArguments

# Downloads are buffered in memory up to this size before spilling over onto disk, so that
# the local destination is only written once the remote file has arrived in full.
GET_FILE_BUFFER_MAX_SIZE = 1024 * 1024  # 1MB

TRANSFER_BLOCK_SIZE = 1024 * 1024  # 1MB

PTY_TERM_TYPE = "vt100"

CONNECT_RETRY_EXCEPTIONS = (OSError, asyncio.TimeoutError, TimeoutError, asyncssh.Error)


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

    ssh_connect_kwargs: dict

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
    "ssh_allow_agent": DataMeta(
        "Whether to use any active SSH agent",
        True,
    ),
    "ssh_look_for_keys": DataMeta(
        "Whether to look for private keys",
        True,
    ),
    "ssh_forward_agent": DataMeta(
        "Whether to enable SSH forward agent (defaults to the SSH config ``ForwardAgent`` value)",
    ),
    "ssh_config_file": DataMeta("SSH config filename"),
    "ssh_known_hosts_file": DataMeta("SSH known_hosts filename"),
    "ssh_strict_host_key_checking": DataMeta(
        "SSH strict host key checking",
        "accept-new",
    ),
    "ssh_connect_kwargs": DataMeta("Override keyword arguments passed into ``asyncssh.connect``"),
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
        "Protocol to use for file transfers. Can be ``sftp`` or ``scp``.",
        "sftp",
    ),
}


class FileTransferClient(Protocol):
    async def getfo(self, remote_filename: str, fl: IO) -> None:
        """
        Get a file from the remote host, writing to the provided file-like object.
        """
        ...

    async def putfo(self, fl: IO, remote_filename: str) -> None:
        """
        Put a file to the remote host, reading from the provided file-like object.
        """
        ...


class SFTPTransferClient:
    def __init__(self, sftp: asyncssh.SFTPClient):
        self.sftp = sftp

    async def getfo(self, remote_filename: str, fl: IO) -> None:
        async with self.sftp.open(remote_filename, "rb") as remote_file:
            while chunk := await remote_file.read(TRANSFER_BLOCK_SIZE):
                fl.write(chunk)

    async def putfo(self, fl: IO, remote_filename: str) -> None:
        async with self.sftp.open(remote_filename, "wb") as remote_file:
            while chunk := fl.read(TRANSFER_BLOCK_SIZE):
                if isinstance(chunk, str):
                    chunk = chunk.encode()
                await remote_file.write(chunk)


class SCPTransferClient:
    """
    asyncssh's scp works on local paths, so transfers go via a local temporary file.
    """

    def __init__(self, connection: asyncssh.SSHClientConnection):
        self.connection = connection

    async def getfo(self, remote_filename: str, fl: IO) -> None:
        with NamedTemporaryFile() as temp_file:
            await asyncssh.scp((self.connection, remote_filename), temp_file.name)
            with open(temp_file.name, "rb") as downloaded_file:
                copyfileobj(downloaded_file, fl)

    async def putfo(self, fl: IO, remote_filename: str) -> None:
        with NamedTemporaryFile() as temp_file:
            while chunk := fl.read(TRANSFER_BLOCK_SIZE):
                if isinstance(chunk, str):
                    chunk = chunk.encode()
                temp_file.write(chunk)
            temp_file.flush()
            await asyncssh.scp(temp_file.name, (self.connection, remote_filename))


class SSHConnector(BaseConnector):
    """
    Connect to hosts over SSH. This is the default connector and all targets default
    to this meaning you do not need to specify it - ie the following two commands
    are identical:

    .. code:: shell

        pyinfra my-host.net ...
        pyinfra @ssh/my-host.net ...
    """

    __examples_doc__ = """
    An inventory file (``inventory.py``) containing a single SSH target with SSH
    forward agent enabled:

    .. code:: python

        hosts = [
            ("my-host.net", {"ssh_forward_agent": True}),
        ]

    Multiple hosts sharing the same SSH username:

    .. code:: python

        hosts = (
            ["my-host-1.net", "my-host-2.net"],
            {"ssh_user": "ssh-user"},
        )

    Multiple hosts with different SSH usernames:

    .. code:: python

        hosts = [
            ("my-host-1.net", {"ssh_user": "ssh-user"}),
            ("my-host-2.net", {"ssh_user": "other-user"}),
        ]
    """

    handles_execution = True

    data_cls = ConnectorData
    data_meta = connector_data_meta
    data: ConnectorData

    client: asyncssh.SSHClientConnection | None = None
    file_transfer_client: FileTransferClient | None = None

    @override
    @staticmethod
    def make_names_data(name):
        yield f"@ssh/{name}", {"ssh_hostname": name}, []

    def make_connect_kwargs(self) -> dict[str, Any]:
        if self.host.data.get("ssh_paramiko_connect_kwargs") is not None:
            logger.warning(
                "`ssh_paramiko_connect_kwargs` is no longer supported, "
                "use `ssh_connect_kwargs` which is passed to `asyncssh.connect`",
            )

        kwargs: dict[str, Any] = {
            "host": self.data["ssh_hostname"] or self.host.name,
            "config": self._get_ssh_config_paths(),
        }

        for key, value in (
            ("username", self.data["ssh_user"]),
            ("port", int(self.data["ssh_port"] or 0)),
            ("connect_timeout", self.state.config.CONNECT_TIMEOUT),
        ):
            if value:
                kwargs[key] = value

        if self.data["ssh_forward_agent"] is not None:
            kwargs["agent_forwarding"] = bool(self.data["ssh_forward_agent"])

        known_hosts_file = self.data["ssh_known_hosts_file"]
        if known_hosts_file:
            kwargs["known_hosts"] = [os.path.expanduser(known_hosts_file)]

        # Password auth (boo!)
        ssh_password = self.data["ssh_password"]
        if ssh_password:
            kwargs["password"] = ssh_password

        # Key auth! An explicit key is used on its own, like `ssh -i`, so the agent
        # remains available for forwarding but is not used to authenticate.
        ssh_key = self.data["ssh_key"]
        if ssh_key:
            private_key, certificate = get_private_key(
                self.state,
                key_filename=ssh_key,
                key_password=self.data["ssh_key_password"],
            )
            kwargs["client_keys"] = [(private_key, certificate)] if certificate else [private_key]
            kwargs["agent_identities"] = []

        # No key or password, so let's have asyncssh look for SSH agents and user keys
        # unless disabled by the user.
        else:
            if not self.data["ssh_allow_agent"]:
                kwargs["agent_path"] = None
            if not self.data["ssh_look_for_keys"]:
                kwargs["client_keys"] = []

        if self.data["ssh_connect_kwargs"]:
            kwargs.update(self.data["ssh_connect_kwargs"])

        return kwargs

    def _get_ssh_config_paths(self) -> list[str] | None | tuple[()]:
        ssh_config_file = self.data["ssh_config_file"]
        if not ssh_config_file:
            return ()  # asyncssh default: ~/.ssh/config if it exists

        ssh_config_file = os.path.expanduser(ssh_config_file)
        if os.path.isfile(ssh_config_file):
            return [ssh_config_file]

        logger.debug("SSH config file does not exist, ignoring: %s", ssh_config_file)
        return None

    def _make_host_key_options(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        # Resolve the known hosts files exactly as asyncssh would (explicit, from
        # the SSH config, or the default) so the policy can read & append to them.
        resolved_options = asyncssh.SSHClientConnectionOptions(**kwargs)
        known_hosts_files = resolve_known_hosts_files(resolved_options.known_hosts)

        if known_hosts_files is None:
            return {"known_hosts": None}

        policy = get_host_key_policy(self.data["ssh_strict_host_key_checking"])
        existing_files = [path for path in known_hosts_files if os.path.isfile(path)]

        return {
            "known_hosts": existing_files or b"",
            "client_factory": lambda: PyinfraSSHClient(policy, known_hosts_files),
        }

    async def _connect_async(self) -> None:
        kwargs = self.make_connect_kwargs()
        kwargs.update(self._make_host_key_options(kwargs))

        logger.debug(
            "Connecting to: %s (%r)",
            kwargs["host"],
            {key: value for key, value in kwargs.items() if key != "password"},
        )

        self.client = await asyncssh.connect(**kwargs)

    @override
    def connect(self) -> None:
        retries = self.data["ssh_connect_retries"]

        try:
            while True:
                try:
                    awaitlet(self._connect_async())
                    return
                except (asyncssh.PermissionDenied, asyncssh.HostKeyNotVerifiable):
                    raise
                except CONNECT_RETRY_EXCEPTIONS:
                    if retries == 0:
                        raise
                    retries -= 1
                    min_delay = self.data["ssh_connect_retry_min_delay"]
                    max_delay = self.data["ssh_connect_retry_max_delay"]
                    awaitlet(asyncio.sleep(uniform(min_delay, max_delay)))
        except asyncssh.PermissionDenied as e:
            auth_kwargs = {}
            if self.data["ssh_user"]:
                auth_kwargs["username"] = self.data["ssh_user"]
            if self.data["ssh_key"]:
                auth_kwargs["key"] = self.data["ssh_key"]
            auth_args = ", ".join(f"{key}={value}" for key, value in auth_kwargs.items())
            raise_connect_error(self.host, f"Authentication error ({auth_args})", e)
        except asyncssh.HostKeyNotVerifiable as e:
            raise_connect_error(self.host, "SSH host key error", e)
        except asyncssh.Error as e:
            raise_connect_error(self.host, "SSH error", e)
        except gaierror as e:
            raise_connect_error(self.host, "Could not resolve hostname", e)
        except (asyncio.TimeoutError, TimeoutError) as e:
            raise_connect_error(self.host, "Could not connect (timeout)", e)
        except OSError as e:
            raise_connect_error(self.host, "Could not connect", e)

    @override
    def disconnect(self) -> None:
        self.file_transfer_client = None

        if self.client is not None:
            self.client.close()
            awaitlet(self.client.wait_closed())
            self.client = None

    async def _execute_async(
        self,
        command: str,
        get_pty: bool,
        stdin,
        timeout: int | None,
        print_output: bool,
    ) -> tuple[int, CommandOutput]:
        assert self.client is not None

        process = await self.client.create_process(
            command,
            term_type=PTY_TERM_TYPE if get_pty else None,
            encoding=None,
        )

        # Write any stdin and then close it
        await write_stdin(stdin, process.stdin)

        try:
            combined_output = await read_output_buffers(
                process.stdout,
                process.stderr,
                timeout=timeout,
                print_output=print_output,
                print_prefix=self.host.print_prefix,
            )
        except TimeoutError:
            process.close()
            raise

        logger.debug("Waiting for exit status...")
        await process.wait()
        exit_status = process.exit_status if process.exit_status is not None else -1
        logger.debug("Command exit status: %i", exit_status)

        return exit_status, combined_output

    @override
    def run_shell_command(
        self,
        command: StringCommand,
        print_output: bool = False,
        print_input: bool = False,
        **arguments: Unpack[ConnectorArguments],
    ) -> tuple[bool, CommandOutput]:
        """
        Execute a command on the specified host.

        Args:
            command (StringCommand): actual command to execute
            print_output (bool): whether to print command output
            print_input (bool): whether to print command input
            arguments: (ConnectorArguments): connector global arguments

        Returns:
            tuple: (bool, CommandOutput)
            Bool indicating success and CommandOutput with stdout/stderr lines.
        """

        _get_pty = arguments.pop("_get_pty", False)
        _timeout = arguments.pop("_timeout", None)
        _stdin = arguments.pop("_stdin", None)
        _success_exit_codes = arguments.pop("_success_exit_codes", None)

        def execute_command() -> tuple[int, CommandOutput]:
            unix_command = make_unix_command_for_host(self.state, self.host, command, **arguments)
            actual_command = unix_command.get_raw_value()

            logger.debug(
                "Running command on %s: (pty=%s) %s",
                self.host.name,
                _get_pty,
                unix_command,
            )

            if print_input:
                echo(f"{self.host.print_prefix}>>> {unix_command}", err=True)

            return awaitlet(
                self._execute_async(
                    actual_command,
                    get_pty=_get_pty,
                    stdin=_stdin,
                    timeout=_timeout,
                    print_output=print_output,
                ),
            )

        return_code, combined_output = execute_command_with_sudo_retry(
            self.host,
            arguments,
            execute_command,
        )

        if _success_exit_codes:
            status = return_code in _success_exit_codes
        else:
            status = return_code == 0

        return status, combined_output

    def get_file_transfer_connection(self) -> FileTransferClient:
        if self.file_transfer_client is None:
            self.file_transfer_client = self._make_file_transfer_client()
        return self.file_transfer_client

    def _make_file_transfer_client(self) -> FileTransferClient:
        assert self.client is not None

        protocol = self.data["ssh_file_transfer_protocol"]

        if protocol == "sftp":
            logger.debug("Using SFTP for file transfer")
            try:
                sftp = awaitlet(self.client.start_sftp_client())
            except asyncssh.Error as e:
                raise ConnectError(
                    (
                        "Unable to establish SFTP connection. Check that the SFTP subsystem "
                        f"for the SSH service at {self.host} is enabled."
                    ),
                ) from e
            return SFTPTransferClient(sftp)

        if protocol == "scp":
            logger.debug("Using SCP for file transfer")
            return SCPTransferClient(self.client)

        raise ConnectError(f"Unsupported file transfer protocol: {protocol}")

    def _get_file(self, remote_filename: str, filename_or_io: str | IO) -> None:
        # Download into a temporary buffer first - opening the destination truncates it, so
        # writing into it directly would destroy the local file if the transfer then failed.
        transfer_client = self.get_file_transfer_connection()
        with SpooledTemporaryFile(max_size=GET_FILE_BUFFER_MAX_SIZE, mode="w+b") as buff:
            awaitlet(transfer_client.getfo(remote_filename, buff))
            buff.seek(0)
            with get_file_io(filename_or_io, "wb") as file_io:
                copyfileobj(buff, file_io)

    @override
    def get_file(
        self,
        remote_filename: str,
        filename_or_io,
        remote_temp_filename=None,
        print_output: bool = False,
        print_input: bool = False,
        **arguments: Unpack[ConnectorArguments],
    ) -> bool:
        """
        Download a file from the remote host using SFTP. Supports download files
        with sudo by copying to a temporary directory with read permissions,
        downloading and then removing the copy.
        """

        _sudo = arguments.get("_sudo", False)
        _su_user = arguments.get("_su_user", None)

        if _sudo or _su_user:
            # Get temp file location
            temp_file = remote_temp_filename or self.host.get_temp_filename(remote_filename)

            # Copy the file to the tempfile location and add read permissions
            command = StringCommand(
                "cp", remote_filename, temp_file, "&&", "chmod", "+r", temp_file
            )

            copy_status, output = self.run_shell_command(
                command,
                print_output=print_output,
                print_input=print_input,
                **arguments,
            )

            if copy_status is False:
                logger.error(f"File download copy temp error: {output.stderr}")
                return False

            try:
                self._get_file(temp_file, filename_or_io)

            # Ensure that, even if we encounter an error, we (attempt to) remove the
            # temporary copy of the file.
            finally:
                remove_status, output = self.run_shell_command(
                    StringCommand("rm", "-f", temp_file),
                    print_output=print_output,
                    print_input=print_input,
                    **arguments,
                )

            if remove_status is False:
                logger.error(f"File download remove temp error: {output.stderr}")
                return False

        else:
            self._get_file(remote_filename, filename_or_io)

        if print_output:
            echo(
                f"{self.host.print_prefix}file downloaded: {remote_filename}",
                err=True,
            )

        return True

    def _put_file(self, filename_or_io, remote_location):
        logger.debug("Attempting upload of %s to %s", filename_or_io, remote_location)

        attempts = 0
        last_e = None

        while attempts < 3:
            try:
                with get_file_io(filename_or_io) as file_io:
                    transfer_client = self.get_file_transfer_connection()
                    awaitlet(transfer_client.putfo(file_io, remote_location))
                return
            except (OSError, asyncssh.Error) as e:
                logger.warning(f"Failed to upload file, retrying: {e}")
                attempts += 1
                last_e = e

        if last_e is not None:
            raise last_e

    @override
    def put_file(
        self,
        filename_or_io,
        remote_filename,
        remote_temp_filename=None,
        print_output: bool = False,
        print_input: bool = False,
        **arguments: Unpack[ConnectorArguments],
    ) -> bool:
        """
        Upload file-ios to the specified host using SFTP. Supports uploading files
        with sudo by uploading to a temporary directory then moving & chowning.
        """

        noauth_arguments = arguments.copy()

        _sudo = noauth_arguments.pop("_sudo", False)
        _sudo_user = noauth_arguments.pop("_sudo_user", False)
        _doas = noauth_arguments.pop("_doas", False)
        _doas_user = noauth_arguments.pop("_doas_user", False)
        _dzdo = noauth_arguments.pop("_dzdo", False)
        _dzdo_user = noauth_arguments.pop("_dzdo_user", False)
        _su_user = noauth_arguments.pop("_su_user", None)

        # _chdir is the only one of the global arguments that could require _sudo to succeed
        # and _sudo isn't present in arguments as removed above
        noauth_arguments.pop("_chdir", False)

        # sudo/su are a little more complicated, as you can only sftp with the SSH
        # user connected, so upload to tmp and copy/chown w/sudo and/or su_user
        if _sudo or _doas or _dzdo or _su_user:
            # Get temp file location
            temp_file = remote_temp_filename or self.host.get_temp_filename(remote_filename)
            self._put_file(filename_or_io, temp_file)

            # Make sure our sudo/su user can access the file
            other_user = _su_user or _sudo_user or _doas_user or _dzdo_user
            if other_user:
                status, output = self.run_shell_command(
                    StringCommand("setfacl", "-m", f"u:{other_user}:r", temp_file),
                    print_output=print_output,
                    print_input=print_input,
                    **noauth_arguments,
                )

                if status is False:
                    logger.error(f"Error on handover to sudo/su user: {output.stderr}")
                    return False

            # Execute run_shell_command w/sudo, etc
            command = StringCommand("cp", temp_file, QuoteString(remote_filename))

            status, output = self.run_shell_command(
                command,
                print_output=print_output,
                print_input=print_input,
                **arguments,
            )

            if status is False:
                logger.error(f"File upload error: {output.stderr}")
                return False

            # Delete the temporary file now that we've successfully copied it
            status, output = self.run_shell_command(
                StringCommand("rm", "-f", temp_file),
                print_output=print_output,
                print_input=print_input,
                **noauth_arguments,
            )

            if status is False:
                logger.error(f"Unable to remove temporary file: {output.stderr}")
                return False

        # No sudo and no su_user, so just upload it!
        else:
            self._put_file(filename_or_io, remote_filename)

        if print_output:
            echo(
                f"{self.host.print_prefix}file uploaded: {remote_filename}",
                err=True,
            )

        return True

    @override
    def check_can_rsync(self) -> None:
        if self.data["ssh_key_password"]:
            raise NotImplementedError(
                "Rsync does not currently work with SSH keys needing passwords."
            )

        if self.data["ssh_password"]:
            raise NotImplementedError("Rsync does not currently work with SSH passwords.")

        if not which("rsync"):
            raise NotImplementedError("The `rsync` binary is not available on this system.")

    @override
    def rsync(
        self,
        src: str,
        dest: str,
        flags: Iterable[str],
        print_output: bool = False,
        print_input: bool = False,
        **arguments: Unpack[ConnectorArguments],
    ):
        _sudo = arguments.pop("_sudo", False)
        _sudo_user = arguments.pop("_sudo_user", False)

        hostname = self.data["ssh_hostname"] or self.host.name
        user = self.data["ssh_user"]
        if user:
            user = f"{user}@"

        ssh_flags = []
        # To avoid asking for interactive input, specify BatchMode=yes
        ssh_flags.append("-o BatchMode=yes")

        known_hosts_file = self.data["ssh_known_hosts_file"]
        if known_hosts_file:
            ssh_flags.append(
                StringCommand(
                    '-o \\"UserKnownHostsFile=',
                    QuoteString(known_hosts_file),
                    '\\"',
                    _separator="",
                ).get_raw_value()
            )  # never trust users

        strict_host_key_checking = self.data["ssh_strict_host_key_checking"]
        if strict_host_key_checking:
            ssh_flags.append(
                StringCommand(
                    '-o \\"StrictHostKeyChecking=',
                    QuoteString(strict_host_key_checking),
                    '\\"',
                    _separator="",
                ).get_raw_value()
            )

        ssh_config_file = self.data["ssh_config_file"]
        if ssh_config_file:
            ssh_flags.append(StringCommand("-F", QuoteString(ssh_config_file)).get_raw_value())

        port = self.data["ssh_port"]
        if port:
            ssh_flags.append(f"-p {port}")

        ssh_key = self.data["ssh_key"]
        if ssh_key:
            ssh_flags.append(f"-i {ssh_key}")

        remote_rsync_command = "rsync"
        if _sudo:
            remote_rsync_command = "sudo rsync"
            if _sudo_user:
                remote_rsync_command = f"sudo -u {_sudo_user} rsync"

        rsync_command = (
            "rsync {rsync_flags} "
            '--rsh "ssh {ssh_flags}" '
            "--rsync-path '{remote_rsync_command}' "
            "{src} {user}{hostname}:{dest}"
        ).format(
            rsync_flags=" ".join(flags),
            ssh_flags=" ".join(ssh_flags),
            remote_rsync_command=remote_rsync_command,
            user=user or "",
            hostname=hostname,
            src=src,
            dest=dest,
        )

        if print_input:
            echo(f"{self.host.print_prefix}>>> {rsync_command}", err=True)

        return_code, output = run_local_process(
            rsync_command,
            print_output=print_output,
            print_prefix=self.host.print_prefix,
        )

        status = return_code == 0
        if not status:
            raise OSError(output.stderr)

        return True
