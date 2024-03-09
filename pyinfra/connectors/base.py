from __future__ import annotations

import abc
from io import IOBase
from typing import (
    TYPE_CHECKING,
    Any,
    Iterable,
    Iterator,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
    get_type_hints,
)

from typing_extensions import TypedDict, Unpack

from pyinfra.api.exceptions import ConnectorDataTypeError
from pyinfra.api.util import raise_if_bad_type

if TYPE_CHECKING:
    from pyinfra.api.arguments import ConnectorArguments
    from pyinfra.api.command import StringCommand
    from pyinfra.api.host import Host, HostData
    from pyinfra.api.state import State

    from .util import CommandOutput


T = TypeVar("T")
default_sentinel = object()


def host_to_connector_data(
    connector_data: Type[T],
    connector_data_meta: dict[str, DataMeta],
    host_data: "HostData",
) -> T:
    data: T = cast(T, {})
    for key, type_ in get_type_hints(connector_data).items():
        value = host_data.get(key, default_sentinel)
        if value is default_sentinel:
            value = connector_data_meta[key].default
        else:
            raise_if_bad_type(
                value,
                type_,
                ConnectorDataTypeError,
                f"Invalid connector data `{key}`:",
            )

        data[key] = value  # type: ignore
    return data


class DataMeta:
    description: str
    default: Any

    def __init__(self, description, default=None) -> None:
        self.description = description
        self.default = default


class ConnectorData(TypedDict, total=False):
    pass


class BaseConnector(abc.ABC):
    state: "State"
    host: "Host"

    handles_execution = False

    data_cls: Type = ConnectorData
    data_meta: dict[str, DataMeta] = {}

    def __init__(self, state: "State", host: "Host"):
        self.state = state
        self.host = host
        self.data = host_to_connector_data(self.data_cls, self.data_meta, host.data)

    @staticmethod
    @abc.abstractmethod
    def make_names_data(name: str) -> Iterator[tuple[str, dict, list[str]]]:
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
