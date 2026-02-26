from __future__ import annotations

import shlex
from io import IOBase
from typing import TYPE_CHECKING, IO, Union, cast

from typing_extensions import Unpack, override

from pyinfra.api.command import StringCommand
from pyinfra.api.exceptions import InventoryError
from pyinfra.api.util import get_file_io

from .base import BaseConnector
from .util import CommandOutput, run_local_process_async

if TYPE_CHECKING:
    from pyinfra.api.arguments import ConnectorArguments


class PowerShellConnector(BaseConnector):
    handles_execution = True

    @override
    @staticmethod
    def make_names_data(name=None):
        if name is not None:
            raise InventoryError("Cannot have more than one @powershell")

        yield "@powershell", {}, ["@powershell"]

    @override
    async def run_shell_command(
        self,
        command: StringCommand,
        print_output: bool = False,
        print_input: bool = False,
        **arguments: Unpack["ConnectorArguments"],
    ) -> tuple[bool, CommandOutput]:
        timeout = arguments.get("_timeout")
        stdin_value = arguments.get("_stdin")
        success_exit_codes = arguments.get("_success_exit_codes")

        wrapped_command = " ".join(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                shlex.quote(command.get_raw_value()),
            ],
        )

        return_code, output = await run_local_process_async(
            wrapped_command,
            stdin=stdin_value,
            timeout=timeout,
            print_output=print_output,
            print_prefix=self.host.print_prefix,
        )

        if success_exit_codes is not None:
            status = return_code in success_exit_codes
        else:
            status = return_code == 0

        return status, output

    @override
    async def put_file(
        self,
        filename_or_io: Union[str, IOBase],
        remote_filename: str,
        remote_temp_filename: str | None = None,
        print_output: bool = False,
        print_input: bool = False,
        **arguments: Unpack["ConnectorArguments"],
    ) -> bool:
        with get_file_io(cast(Union[str, IO], filename_or_io)) as file_io:
            with open(remote_filename, "wb") as output_file:
                data = file_io.read()
                if isinstance(data, str):
                    data = data.encode()
                output_file.write(data)
        return True

    @override
    async def get_file(
        self,
        remote_filename: str,
        filename_or_io: Union[str, IOBase],
        remote_temp_filename: str | None = None,
        print_output: bool = False,
        print_input: bool = False,
        **arguments: Unpack["ConnectorArguments"],
    ) -> bool:
        with open(remote_filename, "rb") as input_file:
            with get_file_io(cast(Union[str, IO], filename_or_io), "wb") as file_io:
                file_io.write(input_file.read())
        return True
