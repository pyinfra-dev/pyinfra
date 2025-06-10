"""Incus / LXD connector

.. Note::
   It requires Incus/LXD agent in order to work properly;
   but it set the first IPv4 address as ssh_hostname when one is found which could be a workaround.

## Usage

.. code-block:: sh

   pyinfra @incus/incus.example.net:instance_name files.get src=/tmp/n.log dest=n.log

   # execute on all instance running on incus.example.net
   pyinfra --debug -vvv --dry @incus/incus.example.net: fact server.LinuxName

"""

# stdlib
import json
from io import IOBase
from os import unlink
from os.path import isfile, realpath
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING, Iterator, Literal, Optional, Union

# pyinfra
from pyinfra import local, logger
from pyinfra.api.command import QuoteString, StringCommand
from pyinfra.api.util import get_file_io
from pyinfra.connectors.base import BaseConnector, DataMeta
from pyinfra.connectors.local import LocalConnector
from pyinfra.connectors.util import (
    CommandOutput,
    extract_control_arguments,
    make_unix_command_for_host,
)
from pyinfra.progress import progress_spinner

if TYPE_CHECKING:
    from pyinfra.api.arguments import ConnectorArguments
    from pyinfra.api.host import Host
    from pyinfra.api.state import State

# dependencies
import click
from typing_extensions import TypedDict, Unpack, override


class ConnectorData(TypedDict):
    lxc_cwd: str
    lxc_env: dict[str, str]
    lxc_user: int


connector_data_meta: dict[str, DataMeta] = {
    "lxc_cwd": DataMeta("Directory to run the command in"),
    "lxc_env": DataMeta("Environment variable to set"),
    "lxc_user": DataMeta("User ID to run the command as"),
}


class IncusConnector(BaseConnector):
    cmd = "incus"
    shell: Literal["ash", "bash", "dash", "posh", "sh", "zsh"] = "sh"
    handles_execution = True

    local: LocalConnector

    remote_instance: str  #: [<remote>:]<instance>
    no_stop: bool = False

    def __init__(self, state: "State", host: "Host"):
        """
        Initialize the Incus connector.

        Args:
            host (str): The hostname/IP address of the target machine
            state (`State`): Pyinfra state object
        """
        super().__init__(state, host)
        self.local = LocalConnector(state, host)
        self.remote_instance = host.name.partition("/")[-1]

    @classmethod
    @override
    def make_names_data(cls, name: str=None) -> Iterator[tuple[str, dict, list[str]]]:
        """
        :param name: ``[<remote>:]<instance>``

        ===========  ================================================
        None         All instances on local connexion
        ===========  ================================================
        example      Look for instance `example` on local connexion
        example:     All instances on the remote named `example`
        example:foo  Look for instance `foo` on remote named `example`
        ===========  ================================================
        """
        command = [cls.cmd, "list --all-projects -c nc -f json"]
        if name is None:
            logger.warning(f"No {cls.cmd} base ID provided! targeting local server")
            remote_instance = ""
        else:
            remote_instance = name.partition("/")[-1] if "/" in name else name
            command += [remote_instance]

        remote, instance = remote_instance.rpartition(":")[::2]
        if remote:
            remote += ":"

        with progress_spinner({f"{cls.cmd} list"}):
            output = local.shell(" ".join(command))
            progress_spinner(f"{cls.cmd} list")

        for row in json.loads(output):
            data = {f"{cls.cmd}_identifier": f"{remote}{row['name']}"}
            for dev in row.get("devices", ""):
                if address := getattr(dev, "ipv4.address", None):
                    data["ssh_hostname"] = address
                    break
            yield (
                f"@{cls.cmd}/{remote}{row['name']}",
                data,
                [f"@{cls.cmd}"],
            )

    @override
    def run_shell_command(
        self,
        command: "StringCommand",
        print_output: bool,
        print_input: bool,
        **arguments: Unpack["ConnectorArguments"],
    ) -> tuple[bool, "CommandOutput"]:
        """Run a shell command to the targeted instance"""
        local_arguments = extract_control_arguments(arguments)

        return self.local.run_shell_command(
            StringCommand(
                self.cmd,
                "exec",
                "-t" if local_arguments.get("_get_pty") else "-T",
                self.remote_instance,
                "--",
                self.shell,
                "-c",
                StringCommand(
                    QuoteString(
                        make_unix_command_for_host(self.state, self.host, command, **arguments)
                    )
                ),
            ),
            print_output=print_output,
            print_input=print_input,
            **local_arguments,
        )

    @override
    def put_file(
        self,
        filename_or_io: Union[str, IOBase],
        remote_filename: str,
        remote_temp_filename: Optional[str] = None,
        print_output: bool = False,
        print_input: bool = False,
        **arguments: Unpack["ConnectorArguments"],
    ) -> bool:
        try:
            filename = realpath(filename_or_io, strict=True) if isfile(filename_or_io) else ""
        except (TypeError, FileNotFoundError):
            filename = ""
        temporary = None
        try:
            if not filename:
                with (
                    get_file_io(filename_or_io) as file_io,
                    NamedTemporaryFile(delete=False) as temporary,
                ):
                    filename = temporary.name
                    data = file_io.read()
                    temporary.write(data.encode() if isinstance(data, str) else data)
                    del data
                    temporary.close()

            status, output = self.local.run_shell_command(
                StringCommand(
                    self.cmd,
                    "file",
                    "push",
                    filename,
                    f"{self.remote_instance}/{remote_filename}",
                ),
                print_output=print_output,
                print_input=print_input,
            )
        finally:
            if temporary is not None:
                unlink(temporary.name)

        if not status:
            raise IOError(output.stderr)

        if print_output:
            click.echo(
                f"{self.host.print_prefix}file uploaded to instance: {remote_filename}",
                err=True,
            )

        return status

    @override
    def get_file(
        self,
        remote_filename: str,
        filename_or_io: Union[str, IOBase],
        remote_temp_filename: Optional[str] = None,
        print_output: bool = False,
        print_input: bool = False,
        **arguments: Unpack["ConnectorArguments"],
    ) -> bool:
        with NamedTemporaryFile() as temporary:
            status, output = self.local.run_shell_command(
                StringCommand(
                    self.cmd,
                    "file",
                    "pull",
                    f"{self.remote_instance}/{remote_filename.lstrip('/')}",
                    temporary.name,
                ),
                print_output=print_output,
                print_input=print_input,
            )
            # Load the temporary file and write it to our file or IO object
            with get_file_io(filename_or_io, "wb") as file_io:
                file_io.write(temporary.read())

        if not status:
            raise IOError(output.stderr)

        if print_output:
            click.echo(
                f"{self.host.print_prefix}file downloaded from instance: {remote_filename}",
                err=True,
            )

        return status


class LXCConnector(IncusConnector):
    cmd = "lxc"
