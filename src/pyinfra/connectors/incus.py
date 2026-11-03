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
    incus_remote: str
    incus_project: str


def _get_incus_instances(command_name: str, remote: str | None) -> list[dict[str, Any]]:
    command_bits: list[str | QuoteString] = [command_name, "list"]
    if remote is not None:
        command_bits.append(QuoteString(f"{remote}:"))
    command = StringCommand(
        *command_bits,
        "--all-projects",
        "--format",
        "json",
        "--fast",
    )

    try:
        output = local.shell(command.get_raw_value())
    except (OSError, PyinfraError) as e:
        raise InventoryError(f"Unable to list {command_name} instances: {e}") from e

    try:
        instances = json.loads(output)
    except json.JSONDecodeError as e:
        raise InventoryError(f"Unable to parse {command_name} instance list as JSON") from e

    if not isinstance(instances, list) or not all(
        isinstance(instance, dict) for instance in instances
    ):
        raise InventoryError(f"Unexpected {command_name} instance list format")

    return instances


def _get_requested_instances(name: str | None) -> dict[str | None, set[str] | None]:
    if name is None:
        return {None: None}

    requested_targets = {part.strip() for part in name.split(",") if part.strip()}
    if not requested_targets:
        raise InventoryError("No Incus instance name provided")

    requests: dict[str | None, set[str] | None] = {}
    for target in requested_targets:
        remote, separator, instance_name = target.rpartition(":")
        if separator and not remote:
            raise InventoryError(f"Invalid Incus target: {target}")
        if not separator:
            instance_name = target

        remote_name = remote if separator else None
        current_names = requests.get(remote_name)
        if not instance_name:
            requests[remote_name] = None
        elif current_names is not None:
            current_names.add(instance_name)
        elif remote_name not in requests:
            requests[remote_name] = {instance_name}

    return requests


def _get_incus_identifier(data: IncusConnectorData) -> str:
    remote = data.get("incus_remote")
    if remote is not None:
        return f"{remote}:{data['incus_name']}"
    return data["incus_name"]


def _get_incus_file_target(instance_name: str, remote_filename: str) -> str:
    return f"{instance_name}/{remote_filename.lstrip('/')}"


class IncusConnector(BaseConnector):
    """
    The ``@incus`` connector targets running containers and virtual machines on the local
    Incus daemon or a configured remote. It executes commands with ``incus exec`` and
    transfers files with ``incus file push`` and ``incus file pull``.

    Inventory includes all projects. Commands use the project reported for each instance.
    Duplicate instance names within one remote are rejected to avoid targeting the wrong
    project. The connector never creates, starts, stops, publishes, or deletes instances.
    Virtual machines require a running ``incus-agent`` and a Unix-like ``sh`` shell. Rsync
    is not supported.

    .. code:: shell

        # Target all running containers and agent-enabled VMs on the local daemon
        pyinfra @incus ...

        # Target one local instance or multiple named instances
        pyinfra @incus/my-instance ...
        pyinfra @incus/container-one,vm-one ...

        # Target all running instances on a configured remote, or one remote instance
        pyinfra @incus/remote: ...
        pyinfra @incus/remote:my-instance ...
    """

    handles_execution = True
    cmd = "incus"

    data_cls = IncusConnectorData
    data_meta = {
        "incus_name": DataMeta("Name of the Incus instance"),
        "incus_type": DataMeta("Instance type: container or virtual-machine"),
        "incus_remote": DataMeta("Configured remote name, or None for the local daemon"),
        "incus_project": DataMeta("Project containing the instance"),
    }
    data: IncusConnectorData

    local: LocalConnector

    def __init__(self, state: State, host: Host) -> None:
        super().__init__(state, host)
        self.local = LocalConnector(state, host)

    @override
    @classmethod
    def make_names_data(cls, name: str | None = None) -> Iterator[tuple[str, dict, list[str]]]:
        requests = _get_requested_instances(name)
        seen_hostnames: set[str] = set()

        for remote, requested_names in requests.items():
            instances = _get_incus_instances(cls.cmd, remote)
            found_names: set[str] = set()

            for instance in instances:
                instance_name = instance.get("name")
                instance_type = instance.get("type")
                if not isinstance(instance_name, str) or not isinstance(instance_type, str):
                    raise InventoryError(f"Unexpected {cls.cmd} instance entry format")

                if requested_names is not None and instance_name not in requested_names:
                    continue
                if instance.get("status") != "Running":
                    continue
                if instance_type not in {"container", "virtual-machine"}:
                    continue

                project = instance.get("project")
                if not isinstance(project, str) or not project:
                    raise InventoryError(
                        f"{cls.cmd} instance {instance_name} has no project information",
                    )

                identifier = f"{remote}:{instance_name}" if remote is not None else instance_name
                hostname = f"@{cls.cmd}/{identifier}"
                if hostname in seen_hostnames:
                    raise InventoryError(
                        f"Duplicate {cls.cmd} instance across projects: {identifier}",
                    )
                seen_hostnames.add(hostname)
                found_names.add(instance_name)

                data = {
                    "incus_name": instance_name,
                    "incus_type": instance_type,
                    "incus_project": project,
                }
                if remote is not None:
                    data["incus_remote"] = remote

                yield hostname, data, [f"@{cls.cmd}"]

            if requested_names is not None:
                missing_names = requested_names - found_names
                if missing_names:
                    prefix = f"{remote}:" if remote is not None else ""
                    names = ", ".join(f"{prefix}{name}" for name in sorted(missing_names))
                    raise InventoryError(f"No running {cls.cmd} instances matching: {names}")
            elif not found_names:
                target = f" on remote {remote}" if remote is not None else ""
                raise InventoryError(f"No running {cls.cmd} instances found{target}")

    def _get_command_bits(self, command: str) -> list[str | QuoteString]:
        command_bits: list[str | QuoteString] = [self.cmd]
        project = self.data.get("incus_project")
        if project is not None and project != "default":
            command_bits.extend(["--project", QuoteString(project)])
        command_bits.append(command)
        return command_bits

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
        instance_name = _get_incus_identifier(self.data)
        status, output = self._run_instance_command(
            StringCommand(
                *self._get_command_bits("exec"),
                QuoteString(instance_name),
                "--",
                "true",
            ),
        )
        if not status:
            raise ConnectError(
                f"Cannot execute commands in {self.cmd} instance {instance_name}. "
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

        command_bits = self._get_command_bits("exec")
        if local_arguments.get("_get_pty"):
            command_bits.append("--force-interactive")

        instance_command = StringCommand(
            *command_bits,
            QuoteString(_get_incus_identifier(self.data)),
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
                    *self._get_command_bits("file"),
                    "push",
                    QuoteString(temp_filename),
                    QuoteString(
                        _get_incus_file_target(
                            _get_incus_identifier(self.data),
                            remote_filename,
                        ),
                    ),
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
                f"{self.host.print_prefix}file uploaded to {self.cmd} instance: {remote_filename}",
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
                    *self._get_command_bits("file"),
                    "pull",
                    QuoteString(
                        _get_incus_file_target(
                            _get_incus_identifier(self.data),
                            remote_filename,
                        ),
                    ),
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
                f"{self.host.print_prefix}file downloaded from {self.cmd} instance: {remote_filename}",
                err=True,
            )

        return status


class LXCConnector(IncusConnector):
    """
    The ``@lxc`` connector provides the same inventory, execution, and file transfer
    behavior as ``@incus``, using the ``lxc`` command instead of ``incus``.
    """

    cmd = "lxc"
