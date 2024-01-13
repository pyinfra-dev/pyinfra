from __future__ import annotations

import abc
from dataclasses import dataclass
from io import IOBase
from typing import TYPE_CHECKING, Iterable, Iterator, Optional, Union

from typing_extensions import Unpack

if TYPE_CHECKING:
    from pyinfra.api.arguments import ConnectorArguments
    from pyinfra.api.command import StringCommand
    from pyinfra.api.host import Host
    from pyinfra.api.state import State

    from .util import CommandOutput


def make_keys(prefix: str, cls):
    class Keys:
        pass

    for key in cls.__dict__:
        if not key.startswith("_"):
            setattr(Keys, key, f"{prefix}_{key}")

    return Keys


@dataclass
class BaseConnector(abc.ABC):
    state: "State"
    host: "Host"

    handles_execution = False

    @staticmethod
    @abc.abstractmethod
    def make_names_data(id: str) -> Iterator[tuple[str, dict, list[str]]]:
        """
        Generates hosts/data/groups information for inventory. This allows a
        single connector reference to generate multiple target hosts.
        """
        ...

    def connect(self) -> None:
        """
        Connect this connector instance.
        """

    def disconnect(self) -> None:
        """
        Disconnect this connector instance.
        """

    @abc.abstractmethod
    def run_shell_command(
        self,
        command: "StringCommand",
        print_output: bool,
        print_input: bool,
        **arguments: Unpack["ConnectorArguments"],
    ) -> tuple[bool, "CommandOutput"]:
        ...

    @abc.abstractmethod
    def put_file(
        self,
        filename_or_io: Union[str, IOBase],
        remote_filename: str,
        remote_temp_filename: Optional[str] = None,
        print_output: bool = False,
        print_input: bool = False,
        **arguments: Unpack["ConnectorArguments"],
    ) -> bool:
        ...

    @abc.abstractmethod
    def get_file(
        self,
        remote_filename: str,
        filename_or_io: Union[str, IOBase],
        remote_temp_filename: Optional[str] = None,
        print_output: bool = False,
        print_input: bool = False,
        **arguments: Unpack["ConnectorArguments"],
    ) -> bool:
        ...

    def check_can_rsync(self):
        raise NotImplementedError("This connector does not support rsync")

    def rsync(
        self,
        src: str,
        dest: str,
        flags: Iterable[str],
        print_output: bool = False,
        print_input: bool = False,
        **arguments: Unpack["ConnectorArguments"],
    ) -> bool:
        raise NotImplementedError("This connector does not support rsync")
