"""Unit tests for the live progress tree routing and the TTY output-loss fixes.

The live tree is only active on a TTY, which pytest cannot easily provide, so
these exercise the routing logic directly rather than through a subprocess.
"""

from unittest.mock import MagicMock

from pyinfra_cli.log import _is_lifecycle_noise
from pyinfra.api.renderable import Diff

from pyinfra_cli.progress import DeployProgress, DetailItem, NodeKind, NodeStatus


def _make_progress(verbose: bool = False) -> DeployProgress:
    # DeployProgress only needs `state` for the op-node helpers, which we drive
    # with a mock below, so a bare mock state is enough here.
    return DeployProgress(MagicMock(), verbose=verbose)


class TestLifecycleNoiseGate:
    """Fix B/C: only lifecycle noise is verbose-gated; deploy output is not."""

    def test_lifecycle_messages_are_noise(self):
        assert _is_lifecycle_noise("Connected")
        assert _is_lifecycle_noise("Ready: apt.packages")
        assert _is_lifecycle_noise("Disconnected")
        assert _is_lifecycle_noise("noop: user already exists")

    def test_deploy_output_is_not_noise(self):
        # Real deploy output / diffs must always route to the host node.
        assert not _is_lifecycle_noise("Will modify /etc/hosts")
        assert not _is_lifecycle_noise("- old line")
        assert not _is_lifecycle_noise("+ new line")
        assert not _is_lifecycle_noise("some command output")


class TestSerialNoWaitLazyNodes:
    """Fix A: --serial/--no-wait never fire operation_start, so the op node must
    be created lazily on first host activity or all host output is dropped."""

    def _mock_state_for_op(self, op_hash: str, host):
        state = MagicMock()
        op_meta = MagicMock()
        op_meta.names = ["server.shell (echo hi)"]
        state.get_op_meta.return_value = op_meta
        state.inventory.get_active_hosts.return_value = [host]
        state.ops = {host: {op_hash: object()}}
        return state

    def test_operation_host_start_creates_op_node_without_operation_start(self):
        progress = _make_progress()
        host = MagicMock()
        host.name = "@fake/web-1"
        op_hash = "abc123"
        state = self._mock_state_for_op(op_hash, host)

        # operation_start is intentionally NOT called (mirrors --serial/--no-wait)
        progress.operation_host_start(state, host, op_hash)

        # The op node was lazily created, and the host node registered so
        # add_host_detail has somewhere to attach output.
        assert op_hash in progress._op_nodes
        assert progress._active_host_node.get(host.name) is not None

        # Host-attributed output is now retained rather than dropped.
        progress.add_host_detail(host.name, "hello from serial")
        node = progress._active_host_node[host.name]
        assert DetailItem(text="hello from serial") in node.detail_lines

    def test_finalize_pending_ops_marks_running_op_success(self):
        progress = _make_progress()
        host = MagicMock()
        host.name = "@fake/web-1"
        op_hash = "abc123"
        state = self._mock_state_for_op(op_hash, host)

        progress.operation_host_start(state, host, op_hash)
        progress.operation_host_success(state, host, op_hash)
        # operation_end never fires under --serial/--no-wait; the op node lingers
        # as RUNNING until finalised.
        assert progress._op_nodes[op_hash].status == NodeStatus.RUNNING

        progress._finalize_pending_ops()
        assert progress._op_nodes[op_hash].status == NodeStatus.OK

    def test_finalize_pending_ops_marks_failed_op_error(self):
        progress = _make_progress()
        host = MagicMock()
        host.name = "@fake/web-1"
        op_hash = "abc123"
        state = self._mock_state_for_op(op_hash, host)

        progress.operation_host_start(state, host, op_hash)
        progress.operation_host_error(state, host, op_hash)

        progress._finalize_pending_ops()
        assert progress._op_nodes[op_hash].status == NodeStatus.ERROR


class TestAddHostDetailDropsWhenNoNode:
    """add_host_detail is a safe no-op when a host has no active node (e.g. a
    line arrives before any phase started); it must never raise."""

    def test_no_node_is_noop(self):
        progress = _make_progress()
        # Should not raise even though no node exists for this host.
        progress.add_host_detail("@fake/unknown", "orphan line")
        assert progress._active_host_node.get("@fake/unknown") is None


class TestNodeKindEnum:
    def test_kinds_exist(self):
        assert NodeKind.OPERATION
        assert NodeKind.HOST


class TestInlineHostStatus:
    """The per-host terminal status shows inline on the host node (green
    Success / cyan No changes), not as a dimmed detail line below."""

    def _host_node(self):
        progress = _make_progress()
        host = MagicMock()
        host.name = "@fake/web-1"
        op_hash = "abc123"
        op_meta = MagicMock()
        op_meta.names = ["server.shell"]
        state = MagicMock()
        state.get_op_meta.return_value = op_meta
        state.inventory.get_active_hosts.return_value = [host]
        state.ops = {host: {op_hash: object()}}
        progress.operation_host_start(state, host, op_hash)
        return progress, progress._active_host_node[host.name]

    def test_success_is_inline_and_green(self):
        progress, node = self._host_node()
        progress.add_host_detail("@fake/web-1", "Success")
        assert node.status == NodeStatus.OK
        assert node.detail == "Success"
        assert node.detail_style == "green"
        # Not duplicated as a dimmed detail line.
        assert node.detail_lines == []

    def test_no_changes_is_inline_and_cyan(self):
        progress, node = self._host_node()
        progress.add_host_detail("@fake/web-1", "No changes")
        assert node.detail == "No changes"
        assert node.detail_style == "cyan"
        assert node.detail_lines == []

    def test_other_output_still_a_detail_line(self):
        progress, node = self._host_node()
        progress.add_host_detail("@fake/web-1", "some command output")
        assert node.detail_lines == [DetailItem(text="some command output")]

    def test_operation_host_success_keeps_inline_detail(self):
        progress, node = self._host_node()
        # Status line arrives first, then the success callback fires.
        progress.add_host_detail("@fake/web-1", "Success")
        state = MagicMock()
        host = MagicMock()
        host.name = "@fake/web-1"
        progress.operation_host_success(state, host, "abc123")
        # The callback must not clobber the inline detail.
        assert node.detail == "Success"
        assert node.detail_style == "green"


class TestHostRenderable:
    """Rich descriptor blocks (diffs, code blocks) are stored as renderable
    detail items and rendered via the registry; they are exempt from the
    running tail-truncation."""

    def _host_node(self):
        progress = _make_progress()
        host = MagicMock()
        host.name = "@fake/web-1"
        op_hash = "abc123"
        op_meta = MagicMock()
        op_meta.names = ["files.put"]
        state = MagicMock()
        state.get_op_meta.return_value = op_meta
        state.inventory.get_active_hosts.return_value = [host]
        state.ops = {host: {op_hash: object()}}
        progress.operation_host_start(state, host, op_hash)
        return progress, progress._active_host_node[host.name]

    def test_add_host_renderable_appends_item(self):
        progress, node = self._host_node()
        diff = Diff("@@ -1,1 +1,1 @@\n- old\n+ new")
        progress.add_host_renderable("@fake/web-1", diff)
        assert node.detail_lines == [DetailItem(descriptor=diff)]

    def test_add_host_renderable_no_node_is_noop(self):
        progress = _make_progress()
        # No active node for this host -> must not raise.
        progress.add_host_renderable("@fake/unknown", Diff("@@ -1 +1 @@\n- a\n+ b"))

    def test_renderable_item_survives_running_truncation(self):
        progress, node = self._host_node()
        # Many plain lines + one renderable; while RUNNING plain lines are
        # tail-trimmed but the renderable is always kept.
        for i in range(10):
            node.add_detail_line(f"line {i}")
        node.add_detail_renderable(Diff("@@ -1 +1 @@\n- a\n+ b"))
        assert node.status == NodeStatus.RUNNING

        table = MagicMock()
        rendered = []
        table.add_row.side_effect = lambda *cols: rendered.append(cols)
        node.render_rows(table)

        # The renderable block is rendered (Padding-wrapped) even though most
        # plain lines were tail-truncated.
        from rich.padding import Padding

        assert any(isinstance(cols[1], Padding) for cols in rendered)
        # Plain lines were tail-truncated (at most RUNNING_DETAIL_LINES kept).
        plain_kept = sum(1 for cols in rendered if "line " in str(cols))
        assert plain_kept <= 5
