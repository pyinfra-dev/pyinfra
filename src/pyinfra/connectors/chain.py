"""
Chained connector — run operations through a stack of connectors.

Syntax::

    @outer/arg/@inner/arg[/@deeper/arg...]

Example::

    pyinfra @ssh/mydoodba/@docker/myodoodev16-odoo-1 files.put ...
    pyinfra @ssh/bastion/@chroot/rootfs server.shell "ls /"

The left-most connector is the *outermost* (it owns the real network
connection); the right-most is the *innermost* (closest to the target).

Each inner connector must implement :meth:`~.base.BaseConnector.wrap_exec_command`,
:meth:`~.base.BaseConnector.wrap_copy_into`, and
:meth:`~.base.BaseConnector.wrap_copy_out` — connectors that only work as an
outer layer (e.g. SSH, which depends on paramiko sockets) will raise
``NotImplementedError`` when used as inner, producing a clear error message.

Two connectors of the same type in the same chain are rejected immediately
because they would share conflicting data keys in ``host.data``.
"""

from __future__ import annotations

import re
from tempfile import mkstemp
from collections.abc import Iterator
from typing import TYPE_CHECKING

from typing_extensions import Unpack, override

from pyinfra.api.exceptions import ConnectError, InventoryError
from pyinfra.api import StringCommand
from pyinfra.api.output import echo

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
    Generic N-level connector chain.

    Instantiated automatically when pyinfra detects ``/@`` in a host name.
    Do not reference this connector directly in inventory files.
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

            # Each connector yields (canonical_name, data, groups) tuples.
            # We take the first yield only (chains are single-host by definition).
            for _sub_name, sub_data, connector_groups in connector_cls.make_names_data(arg_string):
                merged_data.update(sub_data)
                sub_groups.extend(connector_groups)
                break  # only the first yield per connector

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
        command,
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

    @override
    def put_file(
        self,
        filename_or_io,
        remote_filename: str,
        remote_temp_filename: str | None = None,
        print_output: bool = False,
        print_input: bool = False,
        **kwargs,
    ) -> bool:
        """
        Upload ``filename_or_io`` to ``remote_filename`` inside the innermost target.

        Pipeline for a 2-layer chain (ssh → docker):
        1. Upload local file → SSH host temp path (via outer connector's put_file).
        2. ``docker cp <host_tmp> container:<remote_filename>`` (via SSH).
        3. ``rm <host_tmp>`` (via SSH).
        """
        from pyinfra.api.util import get_file_io

        outer = self._connectors[0]
        depth = len(self._connectors)

        # Step 1: upload to the outermost layer's filesystem via a temp path.
        outer_tmp = self.host.get_temp_filename(remote_filename)
        fd, local_tmp = mkstemp()
        import os

        try:
            with get_file_io(filename_or_io) as file_io:
                with open(local_tmp, "wb") as f:
                    data = file_io.read()
                    f.write(data.encode() if isinstance(data, str) else data)

            outer_status = outer.put_file(local_tmp, outer_tmp)
        finally:
            os.close(fd)
            os.remove(local_tmp)

        if not outer_status:
            raise OSError("@chain: failed to upload file to outer connector")

        # Step 2+: for each subsequent layer, copy from the previous temp path
        # deeper into the chain.  Execute these copies via the outer connector
        # (since we only have one real connection — to the outer host).
        prev_tmp = outer_tmp
        for i in range(1, depth):
            connector = self._connectors[i]
            container_id = self._container_ids[i]

            if i < depth - 1:
                # Intermediate layer: copy into this layer's temp path
                next_tmp = self.host.get_temp_filename(f"chain-{i}-{remote_filename}")
                copy_cmd = connector.wrap_copy_into(prev_tmp, next_tmp, container_id)
            else:
                # Innermost layer: copy to the final destination
                next_tmp = remote_filename
                copy_cmd = connector.wrap_copy_into(prev_tmp, remote_filename, container_id)

            # Wrap the copy command through all layers above this one (outer → i-1)
            wrapped_copy = copy_cmd
            for j in range(i - 1, 0, -1):
                wrapped_copy = self._connectors[j].wrap_exec_command(
                    wrapped_copy, self._container_ids[j]
                )

            status, output = outer.run_shell_command(
                wrapped_copy,
                print_output=print_output,
                print_input=print_input,
            )
            if not status:
                raise OSError(f"@chain: layer {i} copy failed: {output.stderr}")

            # Clean up the previous temp on its host
            rm_cmd = StringCommand("rm", "-f", prev_tmp)
            wrapped_rm = rm_cmd
            for j in range(i - 1, 0, -1):
                wrapped_rm = self._connectors[j].wrap_exec_command(
                    wrapped_rm, self._container_ids[j]
                )
            outer.run_shell_command(wrapped_rm, print_output=False, print_input=False)

            prev_tmp = next_tmp

        if print_output:
            echo(
                f"{self.host.print_prefix}file uploaded: {remote_filename}",
                err=True,
            )

        return True

    @override
    def get_file(
        self,
        remote_filename: str,
        filename_or_io,
        remote_temp_filename: str | None = None,
        print_output: bool = False,
        print_input: bool = False,
        **kwargs,
    ) -> bool:
        """
        Download ``remote_filename`` from the innermost target to ``filename_or_io``.

        Reverse of :meth:`put_file` — copies outward layer by layer, then
        downloads to local via the outer connector's get_file.
        """
        outer = self._connectors[0]
        depth = len(self._connectors)

        # Start from innermost: copy out to a temp on the layer above
        # We build the transfer chain in reverse (innermost → outermost).
        current_src = remote_filename

        for i in range(depth - 1, 0, -1):
            connector = self._connectors[i]
            container_id = self._container_ids[i]
            dest_tmp = self.host.get_temp_filename(f"chain-out-{i}-{remote_filename}")

            copy_cmd = connector.wrap_copy_out(current_src, dest_tmp, container_id)

            # Wrap through layers between outer and i (exclusive)
            wrapped_copy = copy_cmd
            for j in range(i - 1, 0, -1):
                wrapped_copy = self._connectors[j].wrap_exec_command(
                    wrapped_copy, self._container_ids[j]
                )

            status, output = outer.run_shell_command(
                wrapped_copy,
                print_output=print_output,
                print_input=print_input,
            )
            if not status:
                raise OSError(f"@chain: layer {i} copy-out failed: {output.stderr}")

            current_src = dest_tmp

        # current_src is now a path on the outer host — download it locally
        outer_status = outer.get_file(current_src, filename_or_io)

        # Clean up outer temp
        outer.run_shell_command(
            StringCommand("rm", "-f", current_src), print_output=False, print_input=False
        )

        if not outer_status:
            raise OSError("@chain: failed to download file from outer connector")

        if print_output:
            echo(
                f"{self.host.print_prefix}file downloaded: {remote_filename}",
                err=True,
            )

        return True
