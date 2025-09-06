from __future__ import annotations

from contextlib import contextmanager
from copy import copy
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generator,
    Optional,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)
from uuid import uuid4

import click
from typing_extensions import Unpack, override

from pyinfra import logger
from pyinfra.connectors.base import BaseConnector
from pyinfra.connectors.util import CommandOutput, remove_any_sudo_askpass_file

from .connectors import get_execution_connector
from .exceptions import ConnectError
from .facts import FactBase, ShortFactBase, get_fact
from .util import memoize, sha1_hash

if TYPE_CHECKING:
    from pyinfra.api.arguments import AllArguments
    from pyinfra.api.inventory import Inventory
    from pyinfra.api.state import State


def extract_callable_datas(
    datas: list[Union[Callable[..., Any], Any]],
) -> Generator[Any, Any, Any]:
    for data in datas:
        # Support for dynamic data, ie @deploy wrapped data defaults where
        # the data is stored on the state temporarily.
        if callable(data):
            data = data()
        yield data


class HostData:
    """
    Combines multiple AttrData's to search for attributes.
    """

    override_datas: dict[str, Any]

    def __init__(self, host: "Host", *datas):
        self.__dict__["host"] = host

        parsed_datas = list(datas)

        # Inject an empty override data so we can assign during deploy
        self.__dict__["override_datas"] = {}
        parsed_datas.insert(0, self.override_datas)

        self.__dict__["datas"] = tuple(parsed_datas)

    def __getattr__(self, key: str):
        for data in extract_callable_datas(self.datas):
            try:
                # Take a shallow copy of the object here, we don't want modifications
                # to host.data.<X> to stick, instead setting host.data.<Y> = is the
                # correct way to achieve this (see __setattr__).
                return copy(data[key])
            except KeyError:
                pass

        raise AttributeError(f"Host `{self.host}` has no data `{key}`")

    @override
    def __setattr__(self, key: str, value: Any):
        self.override_datas[key] = value

    @override
    def __str__(self):
        return str(self.datas)

    def get(self, key: str, default=None):
        return getattr(self, key, default)

    def dict(self):
        out = {}

        # Copy and reverse data objects (such that the first items override
        # the last, matching __getattr__ output).
        datas = list(self.datas)
        datas.reverse()

        for data in extract_callable_datas(datas):
            out.update(data)

        return out


class Host:
    """
    Represents a target host. Thin class that links up to facts and host/group
    data.
    """

    state: "State"
    connector_cls: type[BaseConnector]
    connector: BaseConnector
    connected: bool = False

    # Current context inside an @operation function (op gen stage)
    in_op: bool = False
    in_callback_op: bool = False
    current_op_hash: Optional[str] = None
    current_op_global_arguments: Optional["AllArguments"] = None

    # Current context inside a @deploy function which become part of the op data
    in_deploy: bool = False
    current_deploy_name: Optional[str] = None
    current_deploy_kwargs = None

    # @deploy decorator data is a bit different - we need to handle the case
    # where we're evaluating an operation at runtime (current_op_) but also
    # when ordering operations (current_) outside of an operation context.
    current_op_deploy_data: Optional[dict[str, Any]] = None
    current_deploy_data: Optional[dict[str, Any]] = None

    # Current context during operation execution
    executing_op_hash: Optional[str] = None
    nested_executing_op_hash: Optional[str] = None

    loop_position: list[int]

    # Arbitrary data dictionary connectors may use
    connector_data: dict[str, Any]

    def loop(self, iterable):
        self.loop_position.append(0)
        for i, item in enumerate(iterable):
            self.loop_position[-1] = i
            yield item
        self.loop_position.pop()

    def __init__(
        self,
        name: str,
        inventory: "Inventory",
        groups,
        connector_cls=None,
    ):
        if connector_cls is None:
            connector_cls = get_execution_connector("ssh")
        self.inventory = inventory
        self.groups = groups
        self.connector_cls = connector_cls
        self.name = name

        self.loop_position = []

        self.connector_data = {}

        # Append only list of operation hashes as called on this host, used to
        # generate a DAG to create the final operation order.
        self.op_hash_order: list[str] = []

        # Create the (waterfall data: override, host, group, global)
        self.data = HostData(
            self,
            lambda: inventory.get_override_data(),
            lambda: inventory.get_host_data(name),
            lambda: inventory.get_groups_data(groups),
            lambda: inventory.get_data(),
            # @deploy function data are default values, so come last
            self.get_deploy_data,
        )

    def init(self, state: "State") -> None:
        self.state = state
        self.connector = self.connector_cls(state, self)

        longest_name_len = max([len(host.name) for host in self.inventory])
        padding_diff = longest_name_len - len(self.name)
        self.print_prefix_padding = "".join(" " for _ in range(0, padding_diff))

    @override
    def __str__(self):
        return "{0}".format(self.name)

    @override
    def __repr__(self):
        return "Host({0})".format(self.name)

    @property
    def host_data(self):
        return self.inventory.get_host_data(self.name)

    @property
    def group_data(self):
        return self.inventory.get_groups_data(self.groups)

    @property
    def print_prefix(self) -> str:
        if self.nested_executing_op_hash:
            return "{0}[{1}] {2}{3} ".format(
                click.style(""),  # reset
                click.style(self.name, bold=True),
                click.style("nested", "blue"),
                self.print_prefix_padding,
            )

        return "{0}[{1}]{2} ".format(
            click.style(""),  # reset
            click.style(self.name, bold=True),
            self.print_prefix_padding,
        )

    def style_print_prefix(self, *args, **kwargs) -> str:
        return "{0}[{1}]{2} ".format(
            click.style(""),  # reset
            click.style(self.name, *args, **kwargs),
            self.print_prefix_padding,
        )

    def log(self, message: str, log_func: Callable[[str], Any] = logger.info) -> None:
        log_func(f"{self.print_prefix}{message}")

    def log_styled(
        self, message: str, log_func: Callable[[str], Any] = logger.info, **kwargs
    ) -> None:
        message_styled = click.style(message, **kwargs)
        self.log(message_styled, log_func=log_func)

    def get_deploy_data(self):
        return self.current_op_deploy_data or self.current_deploy_data or {}

    def noop(self, description: str) -> None:
        """
        Log a description for a noop operation.
        """

        handler = logger.info if self.state.print_noop_info else logger.debug
        handler("{0}noop: {1}".format(self.print_prefix, description))

    def when(self, condition: Callable[[], bool]):
        return self.deploy(
            "",
            cast("AllArguments", {"_if": [condition]}),
            {},
            in_deploy=False,
        )

    def arguments(self, **arguments: Unpack["AllArguments"]):
        return self.deploy("", arguments, {}, in_deploy=False)

    @contextmanager
    def deploy(
        self,
        name: str,
        kwargs: Optional["AllArguments"],
        data: Optional[dict],
        in_deploy: bool = True,
    ):
        """
        Wraps a group of operations as a deploy, this should not be used
        directly, instead use ``pyinfra.api.deploy.deploy``.
        """

        # Handle nested deploy names
        if self.current_deploy_name:
            name = "{0} | {1}".format(self.current_deploy_name, name)

        # Store the previous values
        old_in_deploy = self.in_deploy
        old_deploy_name = self.current_deploy_name
        old_deploy_kwargs = self.current_deploy_kwargs
        old_deploy_data = self.current_deploy_data
        self.in_deploy = in_deploy

        # Combine any old _ifs with the new ones
        if old_deploy_kwargs and kwargs:
            old_ifs = old_deploy_kwargs["_if"]
            new_ifs = kwargs["_if"]
            if old_ifs and new_ifs:
                kwargs["_if"] = old_ifs + new_ifs

        # Set the new values
        self.current_deploy_name = name
        self.current_deploy_kwargs = kwargs
        self.current_deploy_data = data
        logger.debug(
            "Starting deploy %s (args=%r, data=%r)",
            name,
            kwargs,
            data,
        )

        yield

        # Restore the previous values
        self.in_deploy = old_in_deploy
        self.current_deploy_name = old_deploy_name
        self.current_deploy_kwargs = old_deploy_kwargs
        self.current_deploy_data = old_deploy_data

        logger.debug(
            "Reset deploy to %s (args=%r, data=%r)",
            old_deploy_name,
            old_deploy_kwargs,
            old_deploy_data,
        )

    @memoize
    def _get_temp_directory(self):
        temp_directory = self.state.config.TEMP_DIR

        if temp_directory is None:
            # Unfortunate, but very hard to avoid, circular dependency, this method is memoized so
            # performance isn't a concern.
            from pyinfra.facts.server import TmpDir

            temp_directory = self.get_fact(TmpDir)

        if not temp_directory:
            temp_directory = self.state.config.DEFAULT_TEMP_DIR

        return temp_directory

    def get_temp_filename(
        self,
        hash_key: Optional[str] = None,
        hash_filename: bool = True,
        *,
        temp_directory: Optional[str] = None,
    ):
        """
        Generate a temporary filename for this deploy.
        """

        temp_directory = temp_directory or self._get_temp_directory()

        if not hash_key:
            hash_key = str(uuid4())

        if hash_filename:
            hash_key = sha1_hash(hash_key)

        return "{0}/pyinfra-{1}".format(temp_directory, hash_key)

    # Host facts
    #

    T = TypeVar("T")

    @overload
    def get_fact(self, name_or_cls: Type[FactBase[T]], *args, **kwargs) -> T: ...

    @overload
    def get_fact(self, name_or_cls: Type[ShortFactBase[T]], *args, **kwargs) -> T: ...

    def get_fact(self, name_or_cls, *args, **kwargs):
        """
        Get a fact for this host, reading from the cache if present.
        """
        return get_fact(self.state, self, name_or_cls, args=args, kwargs=kwargs)

    # Connector proxy
    #

    def _check_state(self) -> None:
        if not self.state:
            raise TypeError("Cannot call this function with no state!")

    def connect(self, reason=None, show_errors: bool = True, raise_exceptions: bool = False):
        """
        Connect to the host using it's configured connector.
        """

        self._check_state()
        if not self.connected:
            self.state.trigger_callbacks("host_before_connect", self)

            try:
                self.connector.connect()
            except ConnectError as e:
                if show_errors:
                    log_message = "{0}{1}".format(
                        self.print_prefix,
                        click.style(e.args[0], "red"),
                    )
                    logger.error(log_message)

                self.state.trigger_callbacks("host_connect_error", self, e)

                if raise_exceptions:
                    raise
            else:
                log_message = "{0}{1}".format(
                    self.print_prefix,
                    click.style("Connected", "green"),
                )
                if reason:
                    log_message = "{0}{1}".format(
                        log_message,
                        " ({0})".format(reason),
                    )

                logger.info(log_message)
                self.state.trigger_callbacks("host_connect", self)
                self.connected = True

    def disconnect(self) -> None:
        """
        Disconnect from the host using it's configured connector.
        """
        self._check_state()

        # Disconnect is an optional function for connectors if needed
        disconnect_func = getattr(self.connector, "disconnect", None)
        if disconnect_func:
            disconnect_func()

        # TODO: consider whether this should be here!
        remove_any_sudo_askpass_file(self)

        self.state.trigger_callbacks("host_disconnect", self)
        self.connected = False

    def run_shell_command(self, *args, **kwargs) -> tuple[bool, CommandOutput]:
        """
        Low level method to execute a shell command on the host via it's configured connector.
        """
        self._check_state()
        return self.connector.run_shell_command(*args, **kwargs)

    def put_file(self, *args, **kwargs) -> bool:
        """
        Low level method to upload a file to the host via it's configured connector.
        """
        self._check_state()
        return self.connector.put_file(*args, **kwargs)

    def get_file(self, *args, **kwargs) -> bool:
        """
        Low level method to download a file from the host via it's configured connector.
        """
        self._check_state()
        return self.connector.get_file(*args, **kwargs)

    # Rsync - optional connector specific ability

    def check_can_rsync(self) -> None:
        self._check_state()
        return self.connector.check_can_rsync()

    def rsync(self, *args, **kwargs) -> bool:
        self._check_state()
        return self.connector.rsync(*args, **kwargs)
