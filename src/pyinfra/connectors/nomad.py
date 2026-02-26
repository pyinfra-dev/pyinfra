from __future__ import annotations

from io import IOBase
from typing import TYPE_CHECKING, Optional, Union

from typing_extensions import TypedDict, Unpack, override

from pyinfra.api import QuoteString, StringCommand
from pyinfra.api.exceptions import ConnectError, InventoryError

from .base import BaseConnector, DataMeta
from .local import LocalConnector
from .util import CommandOutput, async_make_unix_command_for_host, extract_control_arguments

if TYPE_CHECKING:
    from pyinfra.api.arguments import ConnectorArguments
    from pyinfra.api.host import Host
    from pyinfra.api.state import State


class ConnectorData(TypedDict):
    nomad_allocation: str
    nomad_task: Optional[str]


connector_data_meta = {
    "nomad_allocation": DataMeta("Nomad allocation ID"),
    "nomad_task": DataMeta("Nomad task name"),
}


class NomadConnector(BaseConnector):
    handles_execution = True

    data_cls = ConnectorData
    data_meta = connector_data_meta
    data: ConnectorData

    local: LocalConnector

    def __init__(self, state: "State", host: "Host"):
        super().__init__(state, host)
        self.local = LocalConnector(state, host)

    @override
    @staticmethod
    def make_names_data(name: Optional[str] = None):
        if not name:
            raise InventoryError("No allocation provided for @nomad")

        allocation = name
        task = None
        if "/" in name:
            allocation, task = name.split("/", 1)

        yield (
            f"@nomad/{name}",
            {
                "nomad_allocation": allocation,
                "nomad_task": task,
            },
            ["@nomad"],
        )

    @override
    async def connect(self) -> None:
        await self.local.connect()
        command = StringCommand("nomad", "alloc", "status", self.data["nomad_allocation"])
        status, output = await self.local.run_shell_command(command)
        if not status:
            raise ConnectError(output.stderr)

    @override
    async def run_shell_command(
        self,
        command: StringCommand,
        print_output: bool = False,
        print_input: bool = False,
        **command_arguments: Unpack["ConnectorArguments"],
    ) -> tuple[bool, CommandOutput]:
        local_arguments = extract_control_arguments(command_arguments)
        get_pty = command_arguments.get("_get_pty", False)
        stdin_value = command_arguments.get("_stdin", None)

        unix_command = await async_make_unix_command_for_host(
            self.state,
            self.host,
            command,
            **command_arguments,
        )

        exec_command_args = ["nomad", "alloc", "exec"]

        if stdin_value is not None:
            exec_command_args.append("-i")
        if get_pty:
            exec_command_args.append("-t")

        task = self.data.get("nomad_task")
        if task:
            exec_command_args.extend(["-task", task])

        exec_command_args.extend(
            [
                self.data["nomad_allocation"],
                "sh",
                "-c",
                QuoteString(unix_command),
            ],
        )

        return await self.local.run_shell_command(
            StringCommand(*exec_command_args),
            print_output=print_output,
            print_input=print_input,
            **local_arguments,
        )

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
        raise NotImplementedError("The @nomad connector does not support file upload yet")

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
        raise NotImplementedError("The @nomad connector does not support file download yet")
