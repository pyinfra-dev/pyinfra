import os
from shutil import which
from tempfile import mkstemp
from typing import TYPE_CHECKING, Tuple

import click
from typing_extensions import Unpack, override

from pyinfra import logger
from pyinfra.api.command import QuoteString, StringCommand
from pyinfra.api.exceptions import InventoryError
from pyinfra.api.util import get_file_io

from .base import BaseConnector
from .util import (
    CommandOutput,
    execute_command_with_sudo_retry,
    make_unix_command_for_host,
    run_local_process,
)

if TYPE_CHECKING:
    from pyinfra.api.arguments import ConnectorArguments


class LocalConnector(BaseConnector):
    """
    The ``@local`` connector executes changes on the local machine using
    subprocesses. **This connector is only compatible with MacOS & Linux hosts**.

    Examples:

    .. code::

        # Install nginx
        pyinfra inventory.py apt.packages nginx update=true _sudo=true
    """

    handles_execution = True

    @override
    @staticmethod
    def make_names_data(name=None):
        if name is not None:
            raise InventoryError("Cannot have more than one @local")

        yield "@local", {}, ["@local"]

    @override
    def run_shell_command(
        self,
        command: StringCommand,
        print_output: bool = False,
        print_input: bool = False,
        **arguments: Unpack["ConnectorArguments"],
    ) -> Tuple[bool, CommandOutput]:
        """
        Execute a command on the local machine.

        Args:
            command (StringCommand): actual command to execute
            print_output (bool): whether to print command output
            print_input (bool): whether to print command input
            arguments: (ConnectorArguments): connector global arguments

        Returns:
            tuple: (bool, CommandOutput)
            Bool indicating success and CommandOutput with stdout/stderr lines.
        """

        arguments.pop("_get_pty", False)
        _timeout = arguments.pop("_timeout", None)
        _stdin = arguments.pop("_stdin", None)
        _success_exit_codes = arguments.pop("_success_exit_codes", None)

        def execute_command() -> Tuple[int, CommandOutput]:
            unix_command = make_unix_command_for_host(self.state, self.host, command, **arguments)
            actual_command = unix_command.get_raw_value()

            logger.debug("--> Running command on localhost: %s", unix_command)

            if print_input:
                click.echo("{0}>>> {1}".format(self.host.print_prefix, unix_command), err=True)

            return run_local_process(
                actual_command,
                stdin=_stdin,
                timeout=_timeout,
                print_output=print_output,
                print_prefix=self.host.print_prefix,
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

    @override
    def put_file(
        self,
        filename_or_io,
        remote_filename,
        remote_temp_filename=None,  # ignored
        print_output: bool = False,
        print_input: bool = False,
        **arguments,
    ) -> bool:
        """
        Upload a local file or IO object by copying it to a temporary directory
        and then writing it to the upload location.

        Returns:
            bool: Indicating success or failure
        """

        _, temp_filename = mkstemp()

        try:
            # Load our file or IO object and write it to the temporary file
            with get_file_io(filename_or_io) as file_io:
                with open(temp_filename, "wb") as temp_f:
                    data = file_io.read()

                    if isinstance(data, str):
                        data = data.encode()

                    temp_f.write(data)

            # Copy the file using `cp` such that we support sudo/su
            status, output = self.run_shell_command(
                StringCommand("cp", temp_filename, QuoteString(remote_filename)),
                print_output=print_output,
                print_input=print_input,
                **arguments,
            )

            if not status:
                raise IOError(output.stderr)
        finally:
            os.remove(temp_filename)

        if print_output:
            click.echo(
                "{0}file copied: {1}".format(self.host.print_prefix, remote_filename),
                err=True,
            )

        return status

    @override
    def get_file(
        self,
        remote_filename,
        filename_or_io,
        remote_temp_filename=None,  # ignored
        print_output: bool = False,
        print_input: bool = False,
        **arguments,
    ) -> bool:
        """
        Download a local file by copying it to a temporary location and then writing
        it to our filename or IO object.

        Returns:
            bool: Indicating success or failure
        """

        _, temp_filename = mkstemp()

        try:
            # Copy the file using `cp` such that we support sudo/su
            status, output = self.run_shell_command(
                StringCommand("cp", remote_filename, temp_filename),
                print_output=print_output,
                print_input=print_input,
                **arguments,
            )

            if not status:
                raise IOError(output.stderr)

            # Load our file or IO object and write it to the temporary file
            with open(temp_filename, "rb") as temp_f:
                with get_file_io(filename_or_io, "wb") as file_io:
                    data_bytes: bytes

                    data = temp_f.read()
                    if isinstance(data, str):
                        data_bytes = data.encode()
                    else:
                        data_bytes = data

                    file_io.write(data_bytes)
        finally:
            os.remove(temp_filename)

        if print_output:
            click.echo(
                "{0}file copied: {1}".format(self.host.print_prefix, remote_filename),
                err=True,
            )

        return True

    @override
    def check_can_rsync(self) -> None:
        if not which("rsync"):
            raise NotImplementedError("The `rsync` binary is not available on this system.")

    @override
    def rsync(
        self,
        src,
        dest,
        flags,
        print_output: bool = False,
        print_input: bool = False,
        **arguments,
    ) -> bool:
        status, output = self.run_shell_command(
            StringCommand("rsync", " ".join(flags), src, dest),
            print_output=print_output,
            print_input=print_input,
            **arguments,
        )

        if not status:
            raise IOError(output.stderr)

        return True
