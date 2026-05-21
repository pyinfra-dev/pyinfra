from __future__ import annotations

import abc
from io import IOBase
from typing import (
    TYPE_CHECKING,
    Any,
    TypeVar,
    cast,
    get_type_hints,
)
from collections.abc import Iterable, Iterator

from typing_extensions import TypedDict, Unpack

from pyinfra.api.exceptions import ConnectError, ConnectorDataTypeError
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
    connector_data: type[T],
    connector_data_meta: dict[str, DataMeta],
    host_data: HostData,
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
    state: State
    host: Host

    handles_execution = False

    data_cls: type[Any] = ConnectorData
    data_meta: dict[str, DataMeta] = {}

    # Set to the data key that holds this connector's runtime identifier
    # (e.g. "docker_identifier", "chroot_directory"). BaseConnector.get_runtime_id()
    # reads self.data[self.runtime_id_field]. Override get_runtime_id() directly
    # for more complex resolution.
    runtime_id_field: str | None = None

    def __init__(self, state: State, host: Host):
        self.state = state
        self.host = host
        self.data = host_to_connector_data(self.data_cls, self.data_meta, host.data)

    @staticmethod
    @abc.abstractmethod
    def make_names_data(name: str) -> Iterator[tuple[str, dict, list[str]]]:
        """
        Generate inventory targets. This is a staticmethod because each yield will become a new host
        object with a new (ie not this) instance of the connector.
        """

    def connect(self) -> None:
        """
        Connect this connector instance. Should raise ConnectError exceptions to indicate failure.
        """

    def disconnect(self) -> None:
        """
        Disconnect this connector instance.
        """

    @abc.abstractmethod
    def run_shell_command(
        self,
        command: StringCommand,
        print_output: bool,
        print_input: bool,
        **arguments: Unpack[ConnectorArguments],
    ) -> tuple[bool, CommandOutput]:
        """
        Execute a command.

        Args:
            command (StringCommand): actual command to execute
            print_output (bool): whether to print command output
            print_input (bool): whether to print command input
            arguments: (ConnectorArguments): connector global arguments

        Returns:
            tuple: (bool, CommandOutput)
            Bool indicating success and CommandOutput with stdout/stderr lines.
        """

    @abc.abstractmethod
    def put_file(
        self,
        filename_or_io: str | IOBase,
        remote_filename: str,
        remote_temp_filename: str | None = None,
        print_output: bool = False,
        print_input: bool = False,
        **arguments: Unpack[ConnectorArguments],
    ) -> bool:
        """
        Upload a local file or IO object by copying it to a temporary directory
        and then writing it to the upload location.

        Returns:
            bool: indicating success or failure.
        """

    @abc.abstractmethod
    def get_file(
        self,
        remote_filename: str,
        filename_or_io: str | IOBase,
        remote_temp_filename: str | None = None,
        print_output: bool = False,
        print_input: bool = False,
        **arguments: Unpack[ConnectorArguments],
    ) -> bool:
        """
        Download a local file by copying it to a temporary location and then writing
        it to our filename or IO object.

        Returns:
            bool: indicating success or failure.
        """

    def get_runtime_id(self) -> str:
        """
        Return the runtime identifier for this connector when used as an inner
        layer in a :class:`~pyinfra.connectors.chain.ChainedConnector`.

        The default implementation reads ``self.data[self.runtime_id_field]``.
        Override this method for more complex resolution (e.g. combining multiple
        data keys or applying transformations).

        This is called *before* :meth:`connect()`, so it must work solely from
        data available at construction time.

        Raises ``NotImplementedError`` by default if ``runtime_id_field`` is
        ``None`` — connectors that cannot be used as an inner layer do not need
        to implement this.
        """
        if self.runtime_id_field is None:
            raise NotImplementedError(
                f"{self.__class__.__name__} cannot be used as an inner connector in a chain"
            )
        value = self.data.get(self.runtime_id_field)
        if not value:
            raise ConnectError(
                f"{self.__class__.__name__} used as inner layer but "
                f"no {self.runtime_id_field} found in host data"
            )
        return str(value)

    def wrap_exec_command(self, command: StringCommand, container_id: str) -> StringCommand:
        """
        Return a command that, when executed in the *parent* connector's context,
        runs ``command`` inside this connector's target.

        Only connectors that can be used as an *inner* layer in a chain need to
        implement this.  The ``container_id`` parameter carries the runtime
        identifier returned by :meth:`get_runtime_id`.

        Raises ``NotImplementedError`` by default — connectors that cannot be
        used as an inner layer (e.g. SSH, which depends on paramiko sockets
        rather than a plain shell string) are excluded automatically.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} cannot be used as an inner connector in a chain"
        )

    def wrap_copy_into(self, src_on_parent: str, dest: str, container_id: str) -> StringCommand:
        """
        Return a command that, when executed in the *parent* connector's context,
        copies the file at ``src_on_parent`` (a path already present on the parent)
        into this connector's target at ``dest``.

        Same conventions as :meth:`wrap_exec_command`.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} cannot be used as an inner connector in a chain"
        )

    def wrap_copy_out(self, src: str, dest_on_parent: str, container_id: str) -> StringCommand:
        """
        Return a command that, when executed in the *parent* connector's context,
        copies the file at ``src`` inside this connector's target to
        ``dest_on_parent`` on the parent.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} cannot be used as an inner connector in a chain"
        )

    def check_can_rsync(self) -> None:
        raise NotImplementedError("This connector does not support rsync")

    def rsync(
        self,
        src: str,
        dest: str,
        flags: Iterable[str],
        print_output: bool = False,
        print_input: bool = False,
        **arguments: Unpack[ConnectorArguments],
    ) -> bool:
        raise NotImplementedError("This connector does not support rsync")
