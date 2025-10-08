from __future__ import annotations

import os
import tempfile
from random import uniform
from socket import error as socket_error, gaierror
from time import sleep
from typing import IO, TYPE_CHECKING, Any, Iterable, Optional, Tuple

import click
from pssh.clients import SSHClient
from pssh.exceptions import AuthenticationException, ConnectionErrorException, SessionError, Timeout
from typing_extensions import TypedDict, Unpack, override

from pyinfra import logger
from pyinfra.api.command import QuoteString, StringCommand
from pyinfra.api.exceptions import ConnectError
from pyinfra.api.util import get_file_io, memoize

from .base import BaseConnector, DataMeta
from .ssh_util import get_private_key, raise_connect_error
from .util import (
    CommandOutput,
    OutputLine,
    execute_command_with_sudo_retry,
    make_unix_command_for_host,
    write_stdin,
)

if TYPE_CHECKING:
    from pyinfra.api.arguments import ConnectorArguments


class ConnectorData(TypedDict):
    ssh_hostname: str
    ssh_port: int
    ssh_user: str
    ssh_password: str
    ssh_key: str
    ssh_key_password: str

    ssh_allow_agent: bool
    ssh_forward_agent: bool

    ssh_connect_retries: int
    ssh_connect_retry_min_delay: float
    ssh_connect_retry_max_delay: float


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
    "ssh_forward_agent": DataMeta(
        "Whether to enable SSH forward agent",
        False,
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
}


class PSSHConnector(BaseConnector):
    """
    Connect to hosts over SSH using parallel-ssh library. This connector provides
    an alternative to the paramiko-based SSH connector with potentially better
    performance characteristics.

    .. code:: shell

        pyinfra @pssh/my-host.net ...
    """

    __examples_doc__ = """
    An inventory file (``inventory.py``) containing a single SSH target with SSH
    forward agent enabled:

    .. code:: python

        hosts = [
            ("@pssh/my-host.net", {"ssh_forward_agent": True}),
        ]

    Multiple hosts sharing the same SSH username:

    .. code:: python

        hosts = (
            ["@pssh/my-host-1.net", "@pssh/my-host-2.net"],
            {"ssh_user": "ssh-user"},
        )
    """

    handles_execution = True

    data_cls = ConnectorData
    data_meta = connector_data_meta
    data: ConnectorData

    client: Optional[SSHClient] = None

    @override
    @staticmethod
    def make_names_data(name):
        yield "@pssh/{0}".format(name), {"ssh_hostname": name}, []

    def make_pssh_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "host": self.data["ssh_hostname"] or self.host.name,
            "allow_agent": self.data["ssh_allow_agent"],
        }

        # Add user if specified
        if self.data["ssh_user"]:
            kwargs["user"] = self.data["ssh_user"]

        # Add port if specified
        if self.data["ssh_port"]:
            kwargs["port"] = int(self.data["ssh_port"])

        # Add timeout from config
        if self.state.config.CONNECT_TIMEOUT:
            kwargs["timeout"] = self.state.config.CONNECT_TIMEOUT

        # Password authentication
        ssh_password = self.data["ssh_password"]
        if ssh_password:
            kwargs["password"] = ssh_password

        # Key authentication
        ssh_key = self.data["ssh_key"]
        if ssh_key:
            kwargs["pkey"] = ssh_key

        # Key password
        ssh_key_password = self.data["ssh_key_password"]
        if ssh_key_password:
            kwargs["password"] = ssh_key_password

        return kwargs

    @override
    def connect(self) -> None:
        retries = self.data["ssh_connect_retries"]

        try:
            while True:
                try:
                    return self._connect()
                except (SessionError, ConnectionErrorException, gaierror, socket_error, EOFError):
                    if retries == 0:
                        raise
                    retries -= 1
                    min_delay = self.data["ssh_connect_retry_min_delay"]
                    max_delay = self.data["ssh_connect_retry_max_delay"]
                    sleep(uniform(min_delay, max_delay))
        except AuthenticationException as e:
            raise_connect_error(self.host, "SSH authentication error", e)
        except SessionError as e:
            raise_connect_error(self.host, "SSH session error", e)
        except ConnectionErrorException as e:
            raise_connect_error(self.host, "SSH connection error", e)
        except gaierror as e:
            raise_connect_error(self.host, "Could not resolve hostname", e)
        except socket_error as e:
            raise_connect_error(self.host, "Could not connect", e)
        except EOFError as e:
            raise_connect_error(self.host, "EOF error", e)

    def _connect(self) -> None:
        """
        Connect to a single host using parallel-ssh.
        """
        kwargs = self.make_pssh_kwargs()
        hostname = kwargs["host"]
        logger.debug("Connecting to: %s (%r)", hostname, kwargs)

        # Don't catch retry-able exceptions, let them bubble up to connect()
        self.client = SSHClient(**kwargs)

    @override
    def disconnect(self) -> None:
        if self.client:
            try:
                self.client.disconnect()
            except Exception:
                pass
            self.client = None

    @override
    def run_shell_command(
        self,
        command: StringCommand,
        print_output: bool = False,
        print_input: bool = False,
        **arguments: Unpack["ConnectorArguments"],
    ) -> Tuple[bool, CommandOutput]:
        """
        Execute a command on the specified host using parallel-ssh.
        """
        _get_pty = arguments.pop("_get_pty", False)
        _timeout = arguments.pop("_timeout", None)
        _stdin = arguments.pop("_stdin", None)
        _success_exit_codes = arguments.pop("_success_exit_codes", None)

        def execute_command() -> Tuple[int, CommandOutput]:
            unix_command = make_unix_command_for_host(self.state, self.host, command, **arguments)
            actual_command = unix_command.get_raw_value()

            logger.debug(
                "Running command on %s: (pty=%s) %s",
                self.host.name,
                _get_pty,
                unix_command,
            )

            if print_input:
                click.echo("{0}>>> {1}".format(self.host.print_prefix, unix_command), err=True)

            assert self.client is not None

            try:
                # Run the command
                host_out = self.client.run_command(
                    actual_command,
                    use_pty=_get_pty,
                    timeout=_timeout,
                )

                # Collect stdout
                stdout_lines = []
                try:
                    for line in host_out.stdout:
                        if isinstance(line, bytes):
                            line = line.decode('utf-8', errors='replace')
                        stdout_lines.append(line.rstrip('\n'))
                        if print_output:
                            click.echo(
                                "{0}{1}".format(self.host.print_prefix, line.rstrip('\n')),
                                err=True,
                            )
                except Timeout:
                    logger.warning("Timeout reading stdout")

                # Collect stderr
                stderr_lines = []
                try:
                    for line in host_out.stderr:
                        if isinstance(line, bytes):
                            line = line.decode('utf-8', errors='replace')
                        stderr_lines.append(line.rstrip('\n'))
                        if print_output:
                            click.echo(
                                "{0}{1}".format(self.host.print_prefix, line.rstrip('\n')),
                                err=True,
                            )
                except Timeout:
                    logger.warning("Timeout reading stderr")

                # Get exit code
                exit_status = host_out.exit_code if host_out.exit_code is not None else -1

                logger.debug("Command exit status: %i", exit_status)

                # Build combined output
                combined_lines = []
                for line in stdout_lines:
                    combined_lines.append(OutputLine(buffer_name="stdout", line=line))
                for line in stderr_lines:
                    combined_lines.append(OutputLine(buffer_name="stderr", line=line))

                combined_output = CommandOutput(combined_lines=combined_lines)

                return exit_status, combined_output

            except Timeout as e:
                raise ConnectError("Command timeout: {0}".format(e)) from e
            except Exception as e:
                raise ConnectError("Command execution failed: {0}".format(e)) from e

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

    @override
    def get_file(
        self,
        remote_filename: str,
        filename_or_io,
        remote_temp_filename=None,
        print_output: bool = False,
        print_input: bool = False,
        **arguments: Unpack["ConnectorArguments"],
    ) -> bool:
        """
        Download a file from the remote host using SFTP.
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
                logger.error("File download copy temp error: {0}".format(output.stderr))
                return False

            try:
                self._get_file(temp_file, filename_or_io)
            finally:
                remove_status, output = self.run_shell_command(
                    StringCommand("rm", "-f", temp_file),
                    print_output=print_output,
                    print_input=print_input,
                    **arguments,
                )

            if remove_status is False:
                logger.error("File download remove temp error: {0}".format(output.stderr))
                return False
        else:
            self._get_file(remote_filename, filename_or_io)

        if print_output:
            click.echo(
                "{0}file downloaded: {1}".format(self.host.print_prefix, remote_filename),
                err=True,
            )

        return True

    def _get_file(self, remote_filename: str, filename_or_io: str | IO):
        """
        Internal method to download a file using SFTP.
        """
        assert self.client is not None

        try:
            # If filename_or_io is a string (file path), use it directly
            if isinstance(filename_or_io, str):
                self.client.copy_remote_file(remote_filename, filename_or_io)
            else:
                # If it's a file-like object, we need to download to a temp file first
                # then copy the contents to the file-like object
                with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                    tmp_path = tmp_file.name

                try:
                    self.client.copy_remote_file(remote_filename, tmp_path)
                    with open(tmp_path, 'rb') as src:
                        filename_or_io.write(src.read())
                finally:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
        except Exception as e:
            raise ConnectError("Failed to download file: {0}".format(e)) from e

    @override
    def put_file(
        self,
        filename_or_io,
        remote_filename,
        remote_temp_filename=None,
        print_output: bool = False,
        print_input: bool = False,
        **arguments: Unpack["ConnectorArguments"],
    ) -> bool:
        """
        Upload a file to the remote host using SFTP.
        """
        original_arguments = arguments.copy()

        _sudo = arguments.pop("_sudo", False)
        _sudo_user = arguments.pop("_sudo_user", False)
        _doas = arguments.pop("_doas", False)
        _doas_user = arguments.pop("_doas_user", False)
        _su_user = arguments.pop("_su_user", None)

        if _sudo or _doas or _su_user:
            # Get temp file location
            temp_file = remote_temp_filename or self.host.get_temp_filename(remote_filename)
            self._put_file(filename_or_io, temp_file)

            # Make sure our sudo/su user can access the file
            other_user = _su_user or _sudo_user or _doas_user
            if other_user:
                status, output = self.run_shell_command(
                    StringCommand("setfacl", "-m", f"u:{other_user}:r", temp_file),
                    print_output=print_output,
                    print_input=print_input,
                    **arguments,
                )

                if status is False:
                    logger.error("Error on handover to sudo/su user: {0}".format(output.stderr))
                    return False

            # Copy to final location
            command = StringCommand("cp", temp_file, QuoteString(remote_filename))

            status, output = self.run_shell_command(
                command,
                print_output=print_output,
                print_input=print_input,
                **original_arguments,
            )

            if status is False:
                logger.error("File upload error: {0}".format(output.stderr))
                return False

            # Delete the temporary file
            command = StringCommand("rm", "-f", temp_file)

            status, output = self.run_shell_command(
                command,
                print_output=print_output,
                print_input=print_input,
                **arguments,
            )

            if status is False:
                logger.error("Unable to remove temporary file: {0}".format(output.stderr))
                return False
        else:
            self._put_file(filename_or_io, remote_filename)

        if print_output:
            click.echo(
                "{0}file uploaded: {1}".format(self.host.print_prefix, remote_filename),
                err=True,
            )

        return True

    def _put_file(self, filename_or_io, remote_location):
        """
        Internal method to upload a file using SFTP.
        """
        logger.debug("Attempting upload of %s to %s", filename_or_io, remote_location)

        assert self.client is not None

        try:
            # If filename_or_io is a string (file path), use it directly
            if isinstance(filename_or_io, str):
                self.client.copy_file(filename_or_io, remote_location)
            else:
                # If it's a file-like object, we need to write it to a temp file first
                # then upload the temp file
                with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                    tmp_path = tmp_file.name
                    # Copy contents from file-like object to temp file
                    filename_or_io.seek(0)
                    tmp_file.write(filename_or_io.read())

                try:
                    self.client.copy_file(tmp_path, remote_location)
                finally:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
        except Exception as e:
            raise ConnectError("Failed to upload file: {0}".format(e)) from e
