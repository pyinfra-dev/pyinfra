"""
Hierarchical live progress renderer for deploys.

Renders a tree of phases (setup steps, Connecting, Preparing, each operation)
with nested per-host rows. Each node shows a spinner while running and a green
check / red cross (plus error details) when complete; verbose detail lines
(facts, command input/output) nest under the host nodes.

Driven by ``pyinfra.api.state`` callbacks plus explicit phase context managers
for the synchronous setup steps.  Only active on a TTY outside ``--json`` mode;
otherwise the CLI falls back to plain log lines.

Concurrency note: nodes are mutated from many gevent greenlets without locks.
This is safe because greenlets are cooperative — mutations never yield midway —
and rendering happens from the Live refresh ticker between mutations.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from rich.live import Live
from rich.progress_bar import ProgressBar
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text
from typing_extensions import override

from pyinfra.api.renderable import OutputBlock
from pyinfra.api.state import BaseStateCallback

from . import routing
from .console import console
from .renderables import to_renderable

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from pyinfra.api.host import Host
    from pyinfra.api.state import State

CHECK = Text("✓", style="bold green")
CROSS = Text("✗", style="bold red")
SKIP = Text("⤼", style="dim")  # skipped (verbose only)
_SPINNER = "dots"
_REFRESH_PER_SECOND = 12.5

# Number of nested detail lines shown per node while it is still running (the
# full capture is rendered once the node completes / the frame persists).
RUNNING_DETAIL_LINES = 5


class NodeStatus(str, Enum):
    RUNNING = "running"
    OK = "ok"
    ERROR = "error"
    SKIPPED = "skipped"


class NodeKind(str, Enum):
    PHASE = "phase"
    FILE = "file"
    OPERATION = "operation"
    HOST = "host"


# Progress-bar colours per node kind. Steps (phases + operations) are always
# cyan; files are a distinct grouping so they read as blue.
_BAR_STYLE = {
    NodeKind.FILE: "blue",
    NodeKind.OPERATION: "cyan",
    NodeKind.PHASE: "cyan",
}

# Detail-text / status colours matching the completion glyph.
_STATUS_STYLE = {
    NodeStatus.OK: "green",
    NodeStatus.ERROR: "red",
    NodeStatus.SKIPPED: "dim",
    NodeStatus.RUNNING: "dim",
}


def _grid() -> Table:
    """The shared 4-column layout: glyph, label, progress bar/detail, count."""
    table = Table.grid(padding=(0, 1))
    table.add_column(width=1)
    table.add_column()
    table.add_column()
    table.add_column()
    return table


@dataclass
class DetailItem:
    """A nested line under a host node: either plain text or a rich descriptor."""

    text: str | None = None
    descriptor: OutputBlock | None = None
    is_error: bool = False

    @property
    def is_renderable(self) -> bool:
        return self.descriptor is not None


class Node:
    """A single row in the progress tree."""

    def __init__(
        self,
        label: str,
        depth: int = 0,
        total: int | None = None,
        kind: NodeKind = NodeKind.PHASE,
    ):
        self.label = label
        self.depth = depth
        self.kind = kind
        self.status = NodeStatus.RUNNING
        self.detail: str | None = None
        # Optional explicit style for the inline detail; falls back to the
        # status colour when None.
        self.detail_style: str | None = None
        # Verbose per-host lines (fact loads, command input/output, diffs, ...)
        # rendered nested under this node: list of (text, is_error, is_diff).
        # A diff item's ``text`` is a whole diff block rendered via Syntax.
        self.detail_lines: list[DetailItem] = []
        self.total = total  # expected number of children (for the progress bar)
        self.children: list[Node] = []
        self._spinner = Spinner(_SPINNER, style="cyan")

    def add(self, label: str, kind: NodeKind = NodeKind.HOST, total: int | None = None) -> Node:
        child = Node(label, depth=self.depth + 1, total=total, kind=kind)
        self.children.append(child)
        return child

    def remove(self, child: Node) -> None:
        if child in self.children:
            self.children.remove(child)

    def add_detail_line(self, text: str, is_error: bool = False) -> None:
        if text:
            self.detail_lines.append(DetailItem(text=text, is_error=is_error))

    def add_detail_renderable(self, descriptor: OutputBlock) -> None:
        self.detail_lines.append(DetailItem(descriptor=descriptor))

    def succeed(self, detail: str | None = None, detail_style: str | None = None) -> None:
        self.status = NodeStatus.OK
        self.detail = detail
        self.detail_style = detail_style

    def fail(self, detail: str | None = None) -> None:
        self.status = NodeStatus.ERROR
        self.detail = detail

    def skip(self) -> None:
        self.status = NodeStatus.SKIPPED

    @property
    def is_parent(self) -> bool:
        return self.total is not None or bool(self.children)

    @property
    def completed(self) -> int:
        # Skipped hosts are not part of ``total``, so exclude them here too.
        return sum(
            1 for c in self.children if c.status not in (NodeStatus.RUNNING, NodeStatus.SKIPPED)
        )

    @property
    def bar_total(self) -> int:
        if self.total is not None:
            return self.total
        return len(self.children)

    def _glyph(self) -> Text | Spinner:
        if self.status == NodeStatus.OK:
            return CHECK
        if self.status == NodeStatus.ERROR:
            return CROSS
        if self.status == NodeStatus.SKIPPED:
            return SKIP
        return self._spinner

    def render_rows(self, table: Table) -> None:
        indent = "  " * self.depth
        if self.kind == NodeKind.HOST:
            # Dim the "@connector/" prefix so the host name stands out.
            base = "red" if self.status == NodeStatus.ERROR else ""
            label = routing.host_label(self.label, base_style=base, prefix=indent)
        else:
            label = Text(f"{indent}{self.label}")
            if self.status == NodeStatus.ERROR:
                label.stylize("red")
            elif self.kind == NodeKind.FILE:
                label.stylize("bold blue")
            elif self.kind in (NodeKind.PHASE, NodeKind.OPERATION):
                # Match the label to the node's progress-bar colour.
                label.stylize(_BAR_STYLE.get(self.kind, ""))

        if self.is_parent:
            total = max(self.bar_total, 1)
            completed = self.completed
            if self.status == NodeStatus.ERROR:
                bar_style = "red"
            else:
                bar_style = _BAR_STYLE.get(self.kind, "green")
            bar = ProgressBar(
                total=total,
                completed=completed,
                width=30,
                finished_style=bar_style,
                complete_style=bar_style,
            )
            count = Text(f"{completed}/{self.bar_total}", style="dim")
            table.add_row(self._glyph(), label, bar, count)
        else:
            row_detail = (
                Text(
                    self.detail,
                    style=self.detail_style or _STATUS_STYLE.get(self.status, "dim"),
                )
                if self.detail
                else Text("")
            )
            table.add_row(self._glyph(), label, row_detail, Text(""))

        # Nested verbose detail lines: show the tail while running to keep the
        # live region compact; render everything once the node has completed.
        # Rich blocks (diffs, code blocks) are always kept; only plain text
        # lines are tail-truncated while running.
        if self.detail_lines:
            lines = self.detail_lines
            if self.status == NodeStatus.RUNNING:
                plain = [item for item in lines if not item.is_renderable]
                kept_plain = set(id(item) for item in plain[-RUNNING_DETAIL_LINES:])
                lines = [item for item in lines if item.is_renderable or id(item) in kept_plain]
            detail_indent = "  " * (self.depth + 1)
            for item in lines:
                if item.is_renderable:
                    assert item.descriptor is not None
                    table.add_row(
                        Text(""),
                        to_renderable(item.descriptor, indent=len(detail_indent)),
                        Text(""),
                        Text(""),
                    )
                else:
                    table.add_row(
                        Text(""),
                        Text(
                            f"{detail_indent}{item.text}",
                            style="red" if item.is_error else "dim",
                        ),
                        Text(""),
                        Text(""),
                    )

        for child in self.children:
            child.render_rows(table)


class DeployProgress(BaseStateCallback):
    """
    State callback + live tree renderer.

    A single instance is created per run; it owns a Rich ``Live`` region and a
    tree of :class:`Node` objects updated from state callbacks.  Registered via
    ``state.add_callback_handler``.  Each phase — and each operation within the
    Execute phase — gets its own live region so completed sections persist to
    scrollback instead of being cropped when taller than the terminal.

    ``BaseStateCallback`` declares its hooks as ``@staticmethod`` but invokes
    them via ``getattr(handler, name)``, so instance methods work fine at
    runtime; the ``# type: ignore[override]`` markers below acknowledge the
    intentional staticmethod→instance-method shape difference.
    """

    def __init__(self, state: State, verbose: bool = False):
        self.state = state
        self.verbose = verbose
        self._roots: list[Node] = []
        self._op_nodes: dict[str, Node] = {}
        self._op_host_nodes: dict[tuple[str, str], Node] = {}
        self._file_nodes: dict[str, Node] = {}
        self._error_hosts: list[tuple[str, Host]] = []
        self._connect_nodes: dict[str, Node] = {}
        self._connect_root: Node | None = None
        self._prepare_root: Node | None = None
        self._prepare_nodes: dict[str, Node] = {}
        # The most recent node for each host; verbose detail lines attach here.
        self._active_host_node: dict[str, Node] = {}
        self._paused = False
        self._live = self._new_live()

    # Rendering
    #
    def _new_live(self) -> Live:
        # ``get_renderable`` makes the Live pull (and build) the tree lazily at
        # its own refresh rate instead of us re-rendering on every callback.
        return Live(
            get_renderable=self._render,
            console=console,
            refresh_per_second=_REFRESH_PER_SECOND,
            transient=False,
        )

    def _render(self) -> Table:
        table = _grid()
        for root in self._roots:
            root.render_rows(table)
        return table

    @property
    def is_active(self) -> bool:
        """Whether routed host output can reach the display (running or paused)."""
        return self._live.is_started or self._paused

    def add_step(
        self, label: str, total: int | None = None, kind: NodeKind = NodeKind.PHASE
    ) -> Node:
        node = Node(label, total=total, kind=kind)
        self._roots.append(node)
        return node

    def __enter__(self) -> DeployProgress:
        # Start a fresh live region for this phase so completed phases scroll
        # up as static output and the new phase renders below.
        self._roots = []
        self._file_nodes = {}
        self._live = self._new_live()
        self._live.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._finalize_pending_ops()
        self._live.stop()

    def _rotate_region(self) -> None:
        """Persist the current region to scrollback and start a fresh one."""
        self._finalize_pending_ops()
        if self._live.is_started:
            self._live.stop()
        self._roots = []
        self._file_nodes = {}
        self._live = self._new_live()
        self._live.start()

    def _finalize_pending_ops(self) -> None:
        """Mark still-running operation nodes succeed/fail from their children.

        ``operation_end`` finalizes op nodes on the normal path, but the
        ``--serial`` / ``--no-wait`` paths never fire it, so op nodes created
        lazily (see :meth:`_ensure_op_node`) would otherwise linger as running.
        """
        for op_node in self._op_nodes.values():
            if op_node.status != NodeStatus.RUNNING:
                continue
            if any(c.status == NodeStatus.ERROR for c in op_node.children):
                op_node.fail()
            else:
                op_node.succeed()

    def pause(self) -> bool:
        """Clear and stop the live region (e.g. before an interactive prompt).

        Returns True if a live region was actually running (and should be
        resumed afterwards with :meth:`resume`).
        """
        if not self._live.is_started:
            return False
        # transient=True clears the region on stop instead of persisting it,
        # so resume() doesn't render a duplicate frame below.
        self._live.transient = True
        self._live.stop()
        self._paused = True
        return True

    def resume(self) -> None:
        """Restart the live region after :meth:`pause`, keeping the tree."""
        self._paused = False
        self._live = self._new_live()
        self._live.start()

    # Verbose detail routing
    #
    def add_host_detail(self, host_name: str, text: str, is_error: bool = False) -> None:
        """Attach a routed log/echo line to the host's current tree node."""
        node = self._active_host_node.get(host_name)
        if node is None:
            return
        # The per-host terminal status ("Success" / "No changes", optionally
        # "... on retry N") is shown inline on the host node — green for a
        # change, cyan for no change — mirroring the connect/prepare nodes,
        # rather than as a dimmed detail line below.
        if text.startswith("Success"):
            node.succeed(text, detail_style="green")
            return
        if text.startswith("No changes"):
            node.succeed(text, detail_style="cyan")
            return
        node.add_detail_line(text, is_error=is_error)

    def add_host_renderable(self, host_name: str, descriptor: OutputBlock) -> None:
        """Attach a rich renderable block to the host's current tree node."""
        node = self._active_host_node.get(host_name)
        if node is None:
            return
        node.add_detail_renderable(descriptor)

    # Host connect callbacks
    #
    @override
    def host_before_connect(self, state: State, host: Host) -> None:  # type: ignore[override]
        if self._connect_root is None:
            total = sum(1 for h in state.inventory if state.is_host_in_limit(h))
            self._connect_root = self.add_step("Connecting to hosts", total=total)
        node = self._connect_root.add(host.name)
        self._connect_nodes[host.name] = node
        self._active_host_node[host.name] = node

    @override
    def host_connect(self, state: State, host: Host) -> None:  # type: ignore[override]
        node = self._connect_nodes.get(host.name)
        if node:
            node.succeed("connected")
        self._finish_connect_root()

    @override
    def host_connect_error(self, state: State, host: Host, error) -> None:  # type: ignore[override]
        node = self._connect_nodes.get(host.name)
        if node:
            detail = str(error.args[0]) if getattr(error, "args", None) else str(error)
            node.fail(detail)
        self._finish_connect_root()

    def _finish_connect_root(self) -> None:
        root = self._connect_root
        if root is None:
            return
        children = root.children
        # Hosts are added lazily as they start connecting: only conclude once
        # every expected host has been added AND completed.
        if len(children) != root.total:
            return
        if all(c.status != NodeStatus.RUNNING for c in children):
            if any(c.status == NodeStatus.ERROR for c in children):
                root.fail()
            else:
                root.succeed()

    # Prepare phase (driven directly by pyinfra_cli.util._parallel_load_hosts)
    #
    def prepare_start(self, name: str, hosts: Iterable[Host]) -> None:
        """Start a "Preparing <name>" phase with one child row per host."""
        hosts = list(hosts)
        self._prepare_root = self.add_step(f"Preparing {name}", total=len(hosts))
        self._prepare_nodes = {}
        for host in hosts:
            node = self._prepare_root.add(host.name)
            self._prepare_nodes[host.name] = node
            self._active_host_node[host.name] = node

    def prepare_host_done(self, host: Host) -> None:
        """Mark a host's prepare as complete (✗ if the host was failed)."""
        node = self._prepare_nodes.get(host.name)
        if node is None:
            return
        if host in self.state.failed_hosts:
            errors = routing.get_host_errors().get(host.name) or []
            node.fail(errors[0] if errors else "failed")
        else:
            node.succeed("ready")

    def prepare_host_error(self, host: Host, error: BaseException) -> None:
        node = self._prepare_nodes.get(host.name)
        if node is None:
            return
        detail = str(error.args[0]) if getattr(error, "args", None) else str(error)
        node.fail(detail)

    def prepare_end(self) -> None:
        root = self._prepare_root
        if root is None:
            return
        if any(c.status == NodeStatus.ERROR for c in root.children):
            root.fail()
        else:
            root.succeed()
        self._prepare_root = None

    # Operation callbacks
    #
    def _file_node(self, filename: str) -> Node:
        """Get or create the parent node for a task/deploy file."""
        node = self._file_nodes.get(filename)
        if node is None:
            node = self.add_step(filename, kind=NodeKind.FILE)
            self._file_nodes[filename] = node
        return node

    @override
    def operation_start(self, state: State, op_hash) -> None:  # type: ignore[override]
        # One live region per operation: persist the previous operation's
        # subtree to scrollback so long deploys aren't cropped by the terminal
        # height (Rich crops Live content taller than the screen).
        if self._roots:
            self._rotate_region()

        self._ensure_op_node(state, op_hash)

    def _ensure_op_node(self, state: State, op_hash) -> Node:
        """Return the tree node for ``op_hash``, creating it if needed.

        ``operation_start`` normally creates it, but the ``--serial`` and
        ``--no-wait`` execution paths never fire ``operation_start`` (they drive
        hosts directly), so the node is created lazily on first host activity to
        avoid dropping all host output under a TTY.
        """
        op_node = self._op_nodes.get(op_hash)
        if op_node is not None:
            return op_node

        op_meta = state.get_op_meta(op_hash)
        name = ", ".join(op_meta.names) if op_meta.names else "operation"

        # Operation names look like "path/to/file.py | Operation name". Nest the
        # operation under a parent node for its file when present.
        filename: str | None = None
        if " | " in name:
            filename, name = name.split(" | ", 1)

        # Count hosts that will actually run the op (failed hosts are excluded
        # from the active set and never start).
        total = sum(1 for host in state.inventory.get_active_hosts() if op_hash in state.ops[host])

        if filename:
            parent = self._file_node(filename)
            op_node = parent.add(name, kind=NodeKind.OPERATION, total=total or None)
        else:
            op_node = self.add_step(name, total=total or None, kind=NodeKind.OPERATION)

        self._op_nodes[op_hash] = op_node
        return op_node

    @override
    def operation_host_start(self, state: State, host: Host, op_hash) -> None:  # type: ignore[override]
        # Lazily create the op node: --serial/--no-wait never fire
        # operation_start, so without this the node (and all host output) would
        # be dropped.
        parent = self._ensure_op_node(state, op_hash)
        node = parent.add(host.name, kind=NodeKind.HOST)
        self._op_host_nodes[(op_hash, host.name)] = node
        self._active_host_node[host.name] = node

    @override
    def operation_host_skipped(self, state: State, host: Host, op_hash) -> None:  # type: ignore[override]
        # The host doesn't run this operation. By default drop the row entirely
        # so it doesn't linger; in verbose mode keep it with a "skipped" glyph.
        key = (op_hash, host.name)
        node = self._op_host_nodes.get(key)
        parent = self._op_nodes.get(op_hash)
        if node is None or parent is None:
            return
        if self.verbose:
            node.skip()
        else:
            # ``total`` already counts only hosts that run the op, so just drop
            # the transient node created in operation_host_start.
            parent.remove(node)
            self._op_host_nodes.pop(key, None)

    @override
    def operation_host_success(  # type: ignore[override]
        self, state: State, host: Host, op_hash, retry_count: int = 0
    ) -> None:
        node = self._op_host_nodes.get((op_hash, host.name))
        if node:
            # The inline status ("Success"/"No changes") is set from the routed
            # status log line in add_host_detail (which fires first); mark the
            # node OK without clobbering that detail.
            node.succeed(node.detail, detail_style=node.detail_style)

    @override
    def operation_host_error(  # type: ignore[override]
        self, state: State, host: Host, op_hash, retry_count: int = 0, max_retries: int = 0
    ) -> None:
        node = self._op_host_nodes.get((op_hash, host.name))
        if node:
            node.fail("failed")
        self._error_hosts.append((op_hash, host))

    @staticmethod
    def _host_error_detail(state: State, host: Host, op_hash) -> str:
        """Best-effort short error message from the operation's captured stderr."""
        try:
            op_data = state.get_op_data_for_host(host, op_hash)
            stderr = op_data.operation_meta.stderr_lines
        except Exception:
            stderr = []
        for line in stderr:
            line = line.strip()
            if line:
                return line
        return "failed"

    @override
    def operation_end(self, state: State, op_hash) -> None:  # type: ignore[override]
        op_node = self._op_nodes.get(op_hash)
        if op_node is None:
            return
        # Attach the real error message (from captured stderr) to failed hosts;
        # operation_meta is only complete now, after all hosts have run.
        for err_op_hash, host in self._error_hosts:
            if err_op_hash != op_hash:
                continue
            node = self._op_host_nodes.get((op_hash, host.name))
            if node:
                node.fail(self._host_error_detail(state, host, op_hash))
        if any(c.status == NodeStatus.ERROR for c in op_node.children):
            op_node.fail()
        else:
            op_node.succeed()


def is_tree_active(json_output: bool) -> bool:
    """The live tree is used on a TTY outside ``--json`` mode (all verbosity
    levels — verbose detail lines nest under the host nodes)."""
    if json_output:
        return False
    return console.is_terminal


@contextmanager
def step(progress: DeployProgress | None, label: str) -> Iterator[Node | None]:
    """Run a synchronous step as a single spinner→check/cross row.

    Self-contained: renders its own short-lived ``Live`` region so it works
    outside the phase live-regions owned by :class:`DeployProgress`.
    """
    if progress is None:
        yield None
        return

    node = Node(label)

    def render() -> Table:
        table = _grid()
        node.render_rows(table)
        return table

    with Live(
        get_renderable=render,
        console=console,
        refresh_per_second=_REFRESH_PER_SECOND,
        transient=False,
    ):
        try:
            yield node
        except Exception:
            node.fail()
            raise
        else:
            if node.status == NodeStatus.RUNNING:
                node.succeed()
