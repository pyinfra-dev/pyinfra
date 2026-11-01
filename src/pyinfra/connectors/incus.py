from __future__ import annotations

import json
import os
from tempfile import mkstemp
from typing import TYPE_CHECKING, Any, IO, cast

from typing_extensions import Unpack, override

from pyinfra import local
from pyinfra.api import QuoteString, StringCommand
from pyinfra.api.exceptions import ConnectError, InventoryError, PyinfraError
from pyinfra.api.output import echo
from pyinfra.api.util import get_file_io

from .base import BaseConnector, ConnectorData, DataMeta
from .local import LocalConnector
from .util import CommandOutput, extract_control_arguments, make_unix_command_for_host

if TYPE_CHECKING:
    from collections.abc import Iterator
    from io import IOBase

    from pyinfra.api.arguments import ConnectorArguments
    from pyinfra.api.host import Host
    from pyinfra.api.state import State


class IncusConnectorData(ConnectorData, total=False):
    incus_name: str
    incus_type: str


def _get_incus_instances() -> list[dict[str, Any]]:
    try:
        output = local.shell("incus list --format json --fast")
    except (OSError, PyinfraError) as e:
        raise InventoryError(f"Unable to list Incus instances: {e}") from e

    try:
        instances = json.loads(output)
    except json.JSONDecodeError as e:
        raise InventoryError("Unable to parse Incus instance list as JSON") from e

    if not isinstance(instances, list) or not all(
        isinstance(instance, dict) for instance in instances
    ):
        raise InventoryError("Unexpected Incus instance list format")

    return instances


def _get_incus_file_target(instance_name: str, remote_filename: str) -> str:
    return f"{instance_name}/{remote_filename.lstrip('/')}"


class IncusConnector(BaseConnector):
    """
    The ``@incus`` connector targets running containers and virtual machines on the local
    Incus daemon. It executes commands with ``incus exec`` and transfers files with
    ``incus file push`` and ``incus file pull``.

    The connector never creates, starts, stops, publishes, or deletes instances. Virtual
    machines require a running ``incus-agent`` and a Unix-like ``sh`` shell. Named remotes,
    custom projects, and rsync are not supported.

    .. code:: shell

        # Target all running containers and agent-enabled VMs in the current project
        pyinfra @incus ...

        # Target one instance
        pyinfra @incus/my-instance ...

        # Target multiple named instances
        pyinfra @incus/container-one,vm-one ...
    """

    handles_execution = True

    data_cls = IncusConnectorData
    data_meta = {
        "incus_name": DataMeta("Name of the Incus instance"),
        "incus_type": DataMeta("Instance type: container or virtual-machine"),
    }
    data: IncusConnectorData

    local: LocalConnector

    def __init__(self, state: State, host: Host) -> None:
        super().__init__(state, host)
        self.local = LocalConnector(state, host)

    @override
    @staticmethod
    def make_names_data(name: str | None = None) -> Iterator[tuple[str, dict, list[str]]]:
        requested_names = None
        if name is not None:
            requested_names = {part.strip() for part in name.split(",") if part.strip()}
            if not requested_names:
                raise InventoryError("No Incus instance name provided")

        instances = _get_incus_instances()
        found_names = set()

        for instance in instances:
            instance_name = instance.get("name")
            instance_type = instance.get("type")
            if not isinstance(instance_name, str) or not isinstance(instance_type, str):
                raise InventoryError("Unexpected Incus instance entry format")

            if requested_names is not None and instance_name not in requested_names:
                continue
            if instance.get("status") != "Running":
                continue
            if instance_type not in {"container", "virtual-machine"}:
                continue

            found_names.add(instance_name)
            yield (
                f"@incus/{instance_name}",
                {"incus_name": instance_name, "incus_type": instance_type},
                ["@incus"],
            )

        if requested_names is not None:
            missing_names = requested_names - found_names
            if missing_names:
                names = ", ".join(sorted(missing_names))
                raise InventoryError(f"No running Incus instances matching: {names}")
        elif not found_names:
            raise InventoryError("No running Incus instances found")

    def _run_instance_command(
        self,
        command: StringCommand,
        print_output: bool = False,
        print_input: bool = False,
    ) -> tuple[bool, CommandOutput]:
        return self.local.run_shell_command(
            command,
            print_output=print_output,
            print_input=print_input,
        )

    @override
    def connect(self) -> None:
        self.local.connect()
        instance_name = self.data["incus_name"]
        status, output = self._run_instance_command(
            StringCommand("incus", "exec", QuoteString(instance_name), "--", "true"),
        )
        if not status:
            raise ConnectError(
                f"Cannot execute commands in Incus instance {instance_name}. "
                f"VMs require a running incus-agent: {output.stderr}",
            )

    @override
    def run_shell_command(
        self,
        command: StringCommand,
        print_output: bool = False,
        print_input: bool = False,
        **arguments: Unpack[ConnectorArguments],
    ) -> tuple[bool, CommandOutput]:
        local_arguments = extract_control_arguments(arguments)
        command = make_unix_command_for_host(self.state, self.host, command, **arguments)

        command_bits = ["incus", "exec"]
        if local_arguments.get("_get_pty"):
            command_bits.append("--force-interactive")

        instance_command = StringCommand(
            *command_bits,
            QuoteString(self.data["incus_name"]),
            "--",
            "sh",
            "-c",
            QuoteString(command),
        )
        return self.local.run_shell_command(
            instance_command,
            print_output=print_output,
            print_input=print_input,
            **local_arguments,
        )

    @override
    def put_file(
        self,
        filename_or_io: str | IOBase,
        remote_filename: str,
        remote_temp_filename: str | None = None,
        print_output: bool = False,
        print_input: bool = False,
        **arguments: Unpack[ConnectorArguments],
    ) -> bool:
        fd, temp_filename = mkstemp()

        try:
            with get_file_io(cast("str | IO[Any]", filename_or_io)) as file_io:
                with open(temp_filename, "wb") as temp_f:
                    data = file_io.read()
                    if isinstance(data, str):
                        data = data.encode()
                    temp_f.write(data)

            status, output = self._run_instance_command(
                StringCommand(
                    "incus",
                    "file",
                    "push",
                    QuoteString(temp_filename),
                    QuoteString(_get_incus_file_target(self.data["incus_name"], remote_filename)),
                ),
                print_output=print_output,
                print_input=print_input,
            )
        finally:
            os.close(fd)
            os.remove(temp_filename)

        if not status:
            raise OSError(output.stderr)

        if print_output:
            echo(
                f"{self.host.print_prefix}file uploaded to Incus instance: {remote_filename}",
                err=True,
            )

        return status

    @override
    def get_file(
        self,
        remote_filename: str,
        filename_or_io: str | IOBase,
        remote_temp_filename: str | None = None,
        print_output: bool = False,
        print_input: bool = False,
        **arguments: Unpack[ConnectorArguments],
    ) -> bool:
        fd, temp_filename = mkstemp()

        try:
            status, output = self._run_instance_command(
                StringCommand(
                    "incus",
                    "file",
                    "pull",
                    QuoteString(_get_incus_file_target(self.data["incus_name"], remote_filename)),
                    QuoteString(temp_filename),
                ),
                print_output=print_output,
                print_input=print_input,
            )
            if not status:
                raise OSError(output.stderr)

            with open(temp_filename, "rb") as temp_f:
                with get_file_io(cast("str | IO[Any]", filename_or_io), "wb") as file_io:
                    file_io.write(temp_f.read())
        finally:
            os.close(fd)
            os.remove(temp_filename)

        if print_output:
            echo(
                f"{self.host.print_prefix}file downloaded from Incus instance: {remote_filename}",
                err=True,
            )

        return status
