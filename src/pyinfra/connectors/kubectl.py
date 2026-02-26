from __future__ import annotations

import os
from io import IOBase
from tempfile import mkstemp
from typing import TYPE_CHECKING, Any, IO, Optional, Union, cast

import click
from typing_extensions import TypedDict, Unpack, override

from pyinfra.api import QuoteString, StringCommand
from pyinfra.api.exceptions import ConnectError, InventoryError
from pyinfra.api.util import get_file_io

from .base import BaseConnector, DataMeta
from .local import LocalConnector
from .util import CommandOutput, async_make_unix_command_for_host, extract_control_arguments

if TYPE_CHECKING:
    from pyinfra.api.arguments import ConnectorArguments
    from pyinfra.api.host import Host
    from pyinfra.api.state import State


class ConnectorData(TypedDict):
    kubectl_pod: str
    kubectl_namespace: str
    kubectl_container: Optional[str]
    kubectl_context: Optional[str]


connector_data_meta = {
    "kubectl_pod": DataMeta("Kubernetes pod name"),
    "kubectl_namespace": DataMeta("Kubernetes namespace", "default"),
    "kubectl_container": DataMeta("Kubernetes container name"),
    "kubectl_context": DataMeta("Kubernetes context name"),
}


class KubectlConnector(BaseConnector):
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
            raise InventoryError("No pod provided for @kubectl")

        namespace = "default"
        pod_with_container = name

        if "/" in name:
            namespace, pod_with_container = name.split("/", 1)

        pod = pod_with_container
        container = None
        if ":" in pod_with_container:
            pod, container = pod_with_container.split(":", 1)

        yield (
            f"@kubectl/{name}",
            {
                "kubectl_namespace": namespace,
                "kubectl_pod": pod,
                "kubectl_container": container,
            },
            ["@kubectl", f"@kubectl/{namespace}"],
        )

    def _build_base_args(self) -> list[str]:
        args = ["kubectl"]
        context = self.data.get("kubectl_context")
        if context:
            args.extend(["--context", context])
        args.extend(["-n", self.data["kubectl_namespace"]])
        return args

    @override
    async def connect(self) -> None:
        await self.local.connect()
        command = StringCommand(*self._build_base_args(), "get", "pod", self.data["kubectl_pod"])
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

        exec_command_args = [*self._build_base_args(), "exec"]

        if stdin_value is not None:
            exec_command_args.append("-i")
        if get_pty:
            exec_command_args.append("-t")

        exec_command_args.append(self.data["kubectl_pod"])

        container = self.data.get("kubectl_container")
        if container:
            exec_command_args.extend(["-c", container])

        exec_command_args.extend(["--", "sh", "-c", QuoteString(unix_command)])

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
        connector_arguments = cast("ConnectorArguments", arguments)
        fd, temp_filename = mkstemp()
        os.close(fd)

        try:
            with get_file_io(cast(Union[str, IO[Any]], filename_or_io)) as file_io:
                with open(temp_filename, "wb") as temp_f:
                    data = file_io.read()
                    if isinstance(data, str):
                        data = data.encode()
                    temp_f.write(data)

            target = f"{self.data['kubectl_pod']}:{remote_filename}"
            command_parts = [*self._build_base_args(), "cp", temp_filename, target]
            container = self.data.get("kubectl_container")
            if container:
                command_parts.extend(["-c", container])

            status, output = await self.local.run_shell_command(
                StringCommand(*command_parts),
                print_output=print_output,
                print_input=print_input,
                **connector_arguments,
            )
        finally:
            os.remove(temp_filename)

        if not status:
            raise IOError(output.stderr)

        if print_output:
            click.echo(f"{self.host.print_prefix}file copied: {remote_filename}", err=True)

        return status

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
        connector_arguments = cast("ConnectorArguments", arguments)
        fd, temp_filename = mkstemp()
        os.close(fd)

        try:
            source = f"{self.data['kubectl_pod']}:{remote_filename}"
            command_parts = [*self._build_base_args(), "cp", source, temp_filename]
            container = self.data.get("kubectl_container")
            if container:
                command_parts.extend(["-c", container])

            status, output = await self.local.run_shell_command(
                StringCommand(*command_parts),
                print_output=print_output,
                print_input=print_input,
                **connector_arguments,
            )

            with open(temp_filename, "rb") as temp_f:
                with get_file_io(cast(Union[str, IO[Any]], filename_or_io), "wb") as file_io:
                    file_io.write(temp_f.read())
        finally:
            os.remove(temp_filename)

        if not status:
            raise IOError(output.stderr)

        if print_output:
            click.echo(f"{self.host.print_prefix}file copied: {remote_filename}", err=True)

        return status
