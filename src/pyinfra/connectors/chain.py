"""
Chained connector - run operations through a stack of connectors.

See the ``ChainedConnector`` docstring below for the user facing documentation.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from io import IOBase
from typing import IO, TYPE_CHECKING, Any, cast

from typing_extensions import Unpack, override

from pyinfra.api.exceptions import ConnectError, InventoryError, PyinfraError
from pyinfra.api import QuoteString, StringCommand
from pyinfra.api.output import echo
from pyinfra.api.util import get_file_io

from .base import BaseConnector
from .util import extract_control_arguments, make_unix_command_for_host

if TYPE_CHECKING:
    from pyinfra.api.arguments import ConnectorArguments
    from pyinfra.api.host import Host
    from pyinfra.api.state import State

    from .util import CommandOutput

# Segment pattern: @connector_name/optional_arg
# connector names are alphanum + hyphens
_SEGMENT_RE = re.compile(r"^@([A-Za-z0-9_-]+)(?:/(.*))?$")


def _parse_chain(full_name: str) -> list[tuple[str, str | None]]:
    """
    Parse ``@outer/arg/@inner/arg[/@deeper/arg...]`` into an ordered list of
    ``(connector_name, arg_string)`` tuples — outermost first.

    Raises ``InventoryError`` on malformed input or duplicate connector types.
    """
    # Split on "/@" — delimiter cannot appear inside any valid host/image/container name
    raw_segments = full_name.split("/@")
    if len(raw_segments) < 2:
        raise InventoryError(
            f"@chain: expected at least two segments separated by '/@', got: {full_name!r}"
        )

    parsed: list[tuple[str, str | None]] = []
    seen_connectors: set[str] = set()

    for i, seg in enumerate(raw_segments):
        # First segment already starts with "@" (passed as-is from inventory.py).
        # Subsequent segments do NOT start with "@" (it was the split delimiter).
        if i > 0:
            seg = f"@{seg}"

        m = _SEGMENT_RE.match(seg)
        if not m:
            raise InventoryError(
                f"@chain: cannot parse segment {seg!r} — expected @connector[/arg]"
            )

        connector_name = m.group(1)
        arg_string = m.group(2) or None

        if connector_name in seen_connectors:
            raise InventoryError(
                f"@chain: connector type {connector_name!r} appears more than once in the chain "
                f"({full_name!r}).  Two connectors of the same type share conflicting data keys "
                f"(e.g. ssh_hostname). Use SSH ProxyJump in ~/.ssh/config for ssh-over-ssh."
            )
        seen_connectors.add(connector_name)
        parsed.append((connector_name, arg_string))

    return parsed


class ChainedConnector(BaseConnector):
    """
    Run operations through a stack of connectors, targeting hosts that are only
    reachable via other hosts - for example a Docker container on a remote SSH host.

    This connector is instantiated automatically when pyinfra detects the ``/@``
    delimiter in a host name, so you never reference ``@chain`` directly:

    .. code:: shell

        pyinfra @outer/arg/@inner/arg[/@deeper/arg...] ...

    The left-most connector is the *outermost* and owns the real network connection;
    the right-most is the *innermost*, closest to the target. Only the outermost
    connector connects - inner layers merely wrap commands, which are composed into a
    single shell string and executed by the outer connector.

    Uploads are streamed into a ``cat`` running in the innermost target and downloads
    stream back out of one, so no layer ever stores a copy of the payload. Chaining
    through a space constrained hop works whatever the file size.

    ## Writing a chain compatible connector

    To be usable as an *inner* layer a connector must implement ``wrap_exec_command``
    and expose a runtime identifier via ``get_runtime_id`` - by default read from the
    data key named by the ``runtime_id_field`` class attribute. The wrapped command
    must forward stdin and stdout, as file transfers rely on them (hence
    ``docker exec -i``).
    Connectors that only work as an outer layer, such as ``@ssh`` which needs paramiko
    sockets rather than a plain shell string, raise ``NotImplementedError`` and are
    rejected with a clear error.

    ## Limitations

    - The same connector type cannot appear twice in one chain, as both layers would
      share conflicting keys in ``host.data``. Use SSH ``ProxyJump`` in
      ``~/.ssh/config`` for ssh-over-ssh.
    - Every segment must resolve to exactly one host, so inventory connectors that
      expand to many hosts (``@terraform``, ``@vagrant``) cannot be chained.
    - Privilege escalation is applied by the outermost connector, to the whole wrapped
      command. For ``server.shell`` this escalates inside the innermost target, because
      the command is built first and escalated last; for file transfers it escalates
      the ``docker exec`` / ``chroot`` invocation on the outer host.

    .. caution::
        ``_sudo_password`` does not work for inner layers. pyinfra writes a
        ``SUDO_ASKPASS`` helper script onto the host it connects to, but the
        escalated command runs inside the container or chroot where that path does
        not exist. Configure passwordless sudo in the target instead.
    """

    __examples_doc__ = """
    Run an operation inside a Docker container living on a remote SSH host:

    .. code:: shell

        pyinfra @ssh/my-host.net/@docker/my-container server.shell "whoami"

    Upload files into a chroot on a remote build server:

    .. code:: shell

        pyinfra @ssh/build-server/@chroot/rootfs files.sync ./src /opt/app

    Chain into a container on the local machine - the outer connector needs no
    argument of its own:

    .. code:: shell

        pyinfra @local/@docker/my-container server.shell "whoami"
    """

    handles_execution = True

    # Stack of instantiated connectors: index 0 = outermost, -1 = innermost.
    _connectors: list[BaseConnector]
    # Runtime container IDs / chroot paths per inner layer, keyed by layer index.
    _container_ids: dict[int, str]

    def __init__(self, state: State, host: Host):
        super().__init__(state, host)
        self._connectors = []
        self._container_ids = {}

    def _build_connector_stack(self) -> None:
        """
        Instantiate connector objects from ``host.host_data["chain_segments"]``.
        Called lazily during :meth:`connect` so that state/host are fully
        initialised before we look up connector classes.
        """
        from pyinfra.api.connectors import get_all_connectors

        segments: list[tuple[str, str | None]] = self.host.host_data["chain_segments"]
        all_connectors = get_all_connectors()

        for connector_name, _ in segments:
            if connector_name not in all_connectors:
                raise ConnectError(f"@chain: unknown connector {connector_name!r}")
            connector_cls = all_connectors[connector_name]
            self._connectors.append(connector_cls(self.state, self.host))

    @override
    @staticmethod
    def make_names_data(name: str | None) -> Iterator[tuple[str, dict, list[str]]]:  # type: ignore[override]
        if not name:
            raise InventoryError("@chain: no connector chain provided")

        segments = _parse_chain(name)

        # Delegate to each connector's make_names_data to collect & validate data
        # and accumulate all yielded data into one merged dict.
        from pyinfra.api.connectors import get_all_connectors

        all_connectors = get_all_connectors()

        merged_data: dict = {}
        sub_groups: list[str] = ["@chain"]

        for connector_name, arg_string in segments:
            if connector_name not in all_connectors:
                raise InventoryError(f"@chain: unknown connector {connector_name!r}")

            connector_cls = all_connectors[connector_name]

            # Each connector yields (canonical_name, data, groups) tuples. A chain targets
            # exactly one host, so inventory connectors that expand to many hosts are
            # rejected rather than silently truncated.
            sub_names_data = list(connector_cls.make_names_data(arg_string))
            if len(sub_names_data) != 1:
                raise InventoryError(
                    f"@chain: connector {connector_name!r} expands to "
                    f"{len(sub_names_data)} hosts, but a chain targets exactly one host - "
                    "use a separate inventory entry per host instead."
                )

            _sub_name, sub_data, connector_groups = sub_names_data[0]
            merged_data.update(sub_data)
            sub_groups.extend(connector_groups)

        # Store the parsed segments for use during connect()
        merged_data["chain_segments"] = segments

        canonical_name = name  # e.g. "@ssh/mydoodba/@docker/myodoodev16-odoo-1"

        yield (canonical_name, merged_data, sub_groups)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @override
    def connect(self) -> None:
        self._build_connector_stack()

        # Connect the outermost connector (the one that owns the real socket).
        self._connectors[0].connect()

        # For inner connectors we do NOT call their connect() — doing so would
        # trigger a `docker run` / `chroot ls` that either creates an ephemeral
        # container or requires local tool access.  Inner connectors are purely
        # about *command wrapping*, not about establishing a new connection.
        # We store the runtime identifier for each inner layer instead.
        segments: list[tuple[str, str | None]] = self.host.host_data["chain_segments"]

        for i, (connector_name, arg_string) in enumerate(segments[1:], start=1):
            connector = self._connectors[i]
            # Each connector self-reports its own runtime identifier via get_runtime_id().
            runtime_id = self._runtime_id_for(connector, arg_string)
            self._container_ids[i] = runtime_id

    def _runtime_id_for(self, connector: BaseConnector, arg_string: str | None) -> str:
        """
        Return the runtime identifier for an *inner* connector layer.

        Each connector self-reports its identifier via :meth:`~.base.BaseConnector.get_runtime_id`.
        Falls back to the raw ``arg_string`` for connectors that do not implement
        ``get_runtime_id`` (backward compatibility with third-party connectors).
        """
        try:
            return connector.get_runtime_id()
        except NotImplementedError:
            if arg_string:
                return arg_string
            raise ConnectError(
                f"@chain: cannot determine runtime ID for inner connector "
                f"{connector.__class__.__name__!r} — connector does not provide "
                f"get_runtime_id() and no arg_string fallback available."
            )

    @override
    def disconnect(self) -> None:
        # Only disconnect the outermost connector.
        # Inner connectors are "exec wrappers" with no socket to close.
        if self._connectors:
            self._connectors[0].disconnect()

    # ------------------------------------------------------------------
    # Command execution
    # ------------------------------------------------------------------

    @override
    def run_shell_command(
        self,
        command: StringCommand,
        print_output: bool = False,
        print_input: bool = False,
        **arguments: Unpack[ConnectorArguments],
    ) -> tuple[bool, CommandOutput]:
        local_arguments = extract_control_arguments(arguments)

        # Apply sudo/env/chdir wrapping once, for the innermost context.
        wrapped = make_unix_command_for_host(self.state, self.host, command, **arguments)

        # Walk inner layers from innermost to second-outermost, wrapping the
        # command at each level.
        for i in range(len(self._connectors) - 1, 0, -1):
            connector = self._connectors[i]
            container_id = self._container_ids[i]
            wrapped = connector.wrap_exec_command(wrapped, container_id)

        # Execute the final wrapped command via the outermost connector.
        return self._connectors[0].run_shell_command(
            wrapped,
            print_output=print_output,
            print_input=print_input,
            **local_arguments,
        )

    # ------------------------------------------------------------------
    # File transfer
    # ------------------------------------------------------------------

    def _wrap_for_layer(self, command: StringCommand, layer: int) -> StringCommand:
        """
        Wrap ``command`` so the outermost connector executes it inside ``layer``. Layer 0
        is the outermost connector itself, which needs no wrapping.
        """
        for i in range(layer, 0, -1):
            command = self._connectors[i].wrap_exec_command(command, self._container_ids[i])
        return command

    def _check_no_pty(self, arguments: ConnectorArguments) -> None:
        """
        Refuse ``_get_pty`` on a file transfer.

        The payload is streamed over stdin and stdout, and a pseudoTTY merges stderr into
        stdout, echoes the payload back into the output and can deadlock a large transfer.
        Checked here rather than in each connector, so that it holds whatever the outermost
        connector is - only ``@ssh`` refuses the combination on its own initiative.
        """
        if arguments.get("_get_pty"):
            raise PyinfraError(
                "`_get_pty` cannot be used with a file transfer through a chain: the payload "
                "is streamed over stdin/stdout, and a pseudoTTY merges stderr into stdout and "
                "echoes the input back.",
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
        """
        Upload ``filename_or_io`` to ``remote_filename`` inside the innermost target.

        The payload is streamed into a ``cat`` running in the innermost target, so no
        layer stores a copy of it. Chaining through a space constrained hop therefore
        works whatever the file size.

        Privilege escalation applies to the whole wrapped command, as run by the
        outermost connector - see the class docstring.
        """
        self._check_no_pty(arguments)

        write_command = self._wrap_for_layer(
            StringCommand("cat", ">", QuoteString(remote_filename)),
            len(self._connectors) - 1,
        )

        # `IOBase` (the base connector signature) and `IO` (what get_file_io takes) do not
        # overlap for mypy, though every real file object satisfies both.
        with get_file_io(cast("str | IO[Any]", filename_or_io)) as file_io:
            # The payload *is* stdin here, overriding anything the caller passed.
            arguments["_stdin"] = file_io
            status, output = self._connectors[0].run_shell_command(
                write_command,
                print_output=print_output,
                print_input=print_input,
                **arguments,
            )

        if not status:
            raise OSError(f"@chain: failed to upload {remote_filename}: {output.stderr}")

        if print_output:
            echo(f"{self.host.print_prefix}file uploaded: {remote_filename}", err=True)

        return True

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
        """
        Download ``remote_filename`` from the innermost target to ``filename_or_io``.

        Mirror of :meth:`put_file`: the file is streamed out of a ``cat`` running in the
        innermost target straight into the local destination, so no layer stores a copy
        of it.
        """
        self._check_no_pty(arguments)

        read_command = self._wrap_for_layer(
            StringCommand("cat", QuoteString(remote_filename)),
            len(self._connectors) - 1,
        )

        with get_file_io(cast("str | IO[Any]", filename_or_io), "wb") as file_io:
            # The file contents *are* stdout here, overriding anything the caller passed.
            arguments["_stdout"] = file_io
            status, output = self._connectors[0].run_shell_command(
                read_command,
                print_output=print_output,
                print_input=print_input,
                **arguments,
            )

        if not status:
            raise OSError(f"@chain: failed to download {remote_filename}: {output.stderr}")

        if print_output:
            echo(f"{self.host.print_prefix}file downloaded: {remote_filename}", err=True)

        return True
