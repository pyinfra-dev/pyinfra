import os
from io import IOBase
from shutil import which
from tempfile import mkstemp
from typing import TYPE_CHECKING, Any, IO, Iterable, Tuple, Union, cast

import click
from typing_extensions import Unpack, override

from pyinfra import logger
from pyinfra.api.command import QuoteString, StringCommand
from pyinfra.api.exceptions import InventoryError
from pyinfra.api.util import get_file_io

from .base import BaseConnector
from .util import (
    CommandOutput,
    async_make_unix_command_for_host,
    execute_command_with_sudo_retry_async,
    run_local_process_async,
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
    async def run_shell_command(
        self,
        command: StringCommand,
        print_output: bool = False,
        print_input: bool = False,
        **arguments: Unpack["ConnectorArguments"],
    ) -> Tuple[bool, CommandOutput]:
        command_arguments: dict[str, Any] = dict(arguments)

        command_arguments.pop("_get_pty", False)
        timeout = command_arguments.pop("_timeout", None)
        stdin_value = command_arguments.pop("_stdin", None)
        success_exit_codes = command_arguments.pop("_success_exit_codes", None)

        async def execute_command() -> Tuple[int, CommandOutput]:
            unix_command = await async_make_unix_command_for_host(
                self.state,
                self.host,
                command,
                **command_arguments,
            )
            actual_command = unix_command.get_raw_value()

            logger.debug("--> Running command on localhost: %s", unix_command)

            if print_input:
                click.echo(f"{self.host.print_prefix}>>> {unix_command}", err=True)

            return await run_local_process_async(
                actual_command,
                stdin=stdin_value,
                timeout=timeout,
                print_output=print_output,
                print_prefix=self.host.print_prefix,
            )

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

    @override
    async def put_file(
        self,
        filename_or_io: Union[str, IOBase],
        remote_filename: str,
        remote_temp_filename: str | None = None,  # ignored
        print_output: bool = False,
        print_input: bool = False,
        **arguments: Unpack["ConnectorArguments"],
    ) -> bool:
        connector_arguments = cast("ConnectorArguments", arguments)
        _, temp_filename = mkstemp()

        try:
            with get_file_io(cast(Union[str, IO[Any]], filename_or_io)) as file_io:
                with open(temp_filename, "wb") as temp_f:
                    data = file_io.read()

                    if isinstance(data, str):
                        data = data.encode()

                    temp_f.write(data)

            status, output = await self.run_shell_command(
                StringCommand("cp", temp_filename, QuoteString(remote_filename)),
                print_output=print_output,
                print_input=print_input,
                **connector_arguments,
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
    async def get_file(
        self,
        remote_filename: str,
        filename_or_io: Union[str, IOBase],
        remote_temp_filename: str | None = None,  # ignored
        print_output: bool = False,
        print_input: bool = False,
        **arguments: Unpack["ConnectorArguments"],
    ) -> bool:
        connector_arguments = cast("ConnectorArguments", arguments)
        _, temp_filename = mkstemp()

        try:
            status, output = await self.run_shell_command(
                StringCommand("cp", remote_filename, temp_filename),
                print_output=print_output,
                print_input=print_input,
                **connector_arguments,
            )

            if not status:
                raise IOError(output.stderr)

            with open(temp_filename, "rb") as temp_f:
                with get_file_io(cast(Union[str, IO[Any]], filename_or_io), "wb") as file_io:
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
    async def rsync(
        self,
        src: str,
        dest: str,
        flags: Iterable[str],
        print_output: bool = False,
        print_input: bool = False,
        **arguments: Unpack["ConnectorArguments"],
    ) -> bool:
        connector_arguments = cast("ConnectorArguments", arguments)
        status, output = await self.run_shell_command(
            StringCommand("rsync", " ".join(flags), src, dest),
            print_output=print_output,
            print_input=print_input,
            **connector_arguments,
        )

        if not status:
            raise IOError(output.stderr)

        return True
