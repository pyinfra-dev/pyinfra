import os
from tempfile import mkstemp
from typing import TYPE_CHECKING, Optional

import click
from typing_extensions import Unpack, override

from pyinfra import local, logger
from pyinfra.api import QuoteString, StringCommand
from pyinfra.api.exceptions import ConnectError, InventoryError, PyinfraError
from pyinfra.api.util import get_file_io, memoize
from pyinfra.progress import progress_spinner

from .base import BaseConnector
from .local import LocalConnector
from .util import extract_control_arguments, make_unix_command_for_host

if TYPE_CHECKING:
    from pyinfra.api.arguments import ConnectorArguments
    from pyinfra.api.host import Host
    from pyinfra.api.state import State


@memoize
def show_warning() -> None:
    logger.warning("The @chroot connector is in beta!")


class ChrootConnector(BaseConnector):
    """
    The chroot connector allows you to execute operations within another root.
    """

    handles_execution = True

    local: LocalConnector

    def __init__(self, state: "State", host: "Host"):
        super().__init__(state, host)
        self.local = LocalConnector(state, host)

    @override
    @staticmethod
    def make_names_data(name: Optional[str] = None):
        if not name:
            raise InventoryError("No directory provided!")

        show_warning()

        yield "@chroot/{0}".format(name), {
            "chroot_directory": "/{0}".format(name.lstrip("/")),
        }, ["@chroot"]

    @override
    def connect(self) -> None:
        self.local.connect()

        chroot_directory = self.host.data.chroot_directory

        try:
            with progress_spinner({"chroot run"}):
                local.shell(
                    "chroot {0} ls".format(chroot_directory),
                    splitlines=True,
                )
        except PyinfraError as e:
            raise ConnectError(e.args[0])

        self.host.connector_data["chroot_directory"] = chroot_directory

    @override
    def run_shell_command(
        self,
        command,
        print_output: bool = False,
        print_input: bool = False,
        **command_arguments: Unpack["ConnectorArguments"],
    ):
        local_arguments = extract_control_arguments(command_arguments)

        chroot_directory = self.host.connector_data["chroot_directory"]

        command = make_unix_command_for_host(self.state, self.host, command, **command_arguments)
        command = QuoteString(command)

        logger.debug("--> Running chroot command on (%s): %s", chroot_directory, command)

        chroot_command = StringCommand(
            "chroot",
            chroot_directory,
            "sh",
            "-c",
            command,
        )

        return self.local.run_shell_command(
            chroot_command,
            print_output=print_output,
            print_input=print_input,
            **local_arguments,
        )

    @override
    def put_file(
        self,
        filename_or_io,
        remote_filename,
        remote_temp_filename=None,  # ignored
        print_output: bool = False,
        print_input: bool = False,
        **kwargs,  # ignored (sudo/etc)
    ):
        _, temp_filename = mkstemp()

        try:
            # Load our file or IO object and write it to the temporary file
            with get_file_io(filename_or_io) as file_io:
                with open(temp_filename, "wb") as temp_f:
                    data = file_io.read()

                    if isinstance(data, str):
                        data = data.encode()

                    temp_f.write(data)

            chroot_directory = self.host.connector_data["chroot_directory"]
            chroot_command = StringCommand(
                "cp",
                temp_filename,
                f"{chroot_directory}/{remote_filename}",
            )

            status, output = self.local.run_shell_command(
                chroot_command,
                print_output=print_output,
                print_input=print_input,
            )
        finally:
            os.remove(temp_filename)

        if not status:
            raise IOError(output.stderr)

        if print_output:
            click.echo(
                "{0}file uploaded to chroot: {1}".format(
                    self.host.print_prefix,
                    remote_filename,
                ),
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
        **kwargs,  # ignored (sudo/etc)
    ):
        _, temp_filename = mkstemp()

        try:
            chroot_directory = self.host.connector_data["chroot_directory"]
            chroot_command = StringCommand(
                "cp",
                f"{chroot_directory}/{remote_filename}",
                temp_filename,
            )

            status, output = self.local.run_shell_command(
                chroot_command,
                print_output=print_output,
                print_input=print_input,
            )

            # Load the temporary file and write it to our file or IO object
            with open(temp_filename, "rb") as temp_f:
                with get_file_io(filename_or_io, "wb") as file_io:
                    data = temp_f.read()
                    data_bytes: bytes

                    if isinstance(data, str):
                        data_bytes = data.encode()
                    else:
                        data_bytes = data

                    file_io.write(data_bytes)
        finally:
            os.remove(temp_filename)

        if not status:
            raise IOError(output.stderr)

        if print_output:
            click.echo(
                "{0}file downloaded from chroot: {1}".format(
                    self.host.print_prefix,
                    remote_filename,
                ),
                err=True,
            )

        return status
