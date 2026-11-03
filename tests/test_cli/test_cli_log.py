"""Unit tests for the CLI log handler's rich-descriptor routing."""

import logging
from unittest.mock import MagicMock, patch

import pytest

from pyinfra.api.renderable import Diff

from pyinfra_cli.console import echo
from pyinfra_cli.log import LogHandler
from pyinfra_cli.progress import DeployProgress, DetailItem, Node, NodeStatus


def _rich_record(descriptor, host="@fake/web-1") -> logging.LogRecord:
    record = logging.LogRecord(
        name="pyinfra",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=str(descriptor),
        args=(),
        exc_info=None,
    )
    record.pyinfra_rich = descriptor
    record.pyinfra_host = host
    return record


DIFF = Diff("@@ -1,1 +1,1 @@\n- old line\n+ new line")


class TestRichRouting:
    def test_descriptor_routed_to_tree(self):
        tree = MagicMock()
        tree.is_active = True
        handler = LogHandler()

        with patch("pyinfra_cli.log.routing.get_tree", return_value=tree):
            handler.emit(_rich_record(DIFF))

        tree.add_host_renderable.assert_called_once()
        host_name, descriptor = tree.add_host_renderable.call_args.args
        assert host_name == "@fake/web-1"
        # The descriptor is passed intact (not stringified / re-parsed).
        assert descriptor is DIFF

    def test_descriptor_printed_when_no_tree(self):
        handler = LogHandler()

        with (
            patch("pyinfra_cli.log.routing.get_tree", return_value=None),
            patch("pyinfra_cli.log.console") as console,
        ):
            handler.emit(_rich_record(DIFF))

        console.print.assert_called_once()
        # Rendered via the registry (a Syntax/Padding renderable), not a string.
        (renderable,) = console.print.call_args.args
        assert not isinstance(renderable, str)

    def test_descriptor_printed_when_tree_inactive(self):
        tree = MagicMock()
        tree.is_active = False
        handler = LogHandler()

        with (
            patch("pyinfra_cli.log.routing.get_tree", return_value=tree),
            patch("pyinfra_cli.log.console") as console,
        ):
            handler.emit(_rich_record(DIFF))

        tree.add_host_renderable.assert_not_called()
        console.print.assert_called_once()


@pytest.mark.parametrize("message", ["Success", "Success: deployed", "No changes required"])
@pytest.mark.parametrize("source", ["log", "echo"])
def test_status_like_output_is_retained(message, source):
    host_name = "@fake/web-1"
    tree = DeployProgress(MagicMock())
    tree._live = MagicMock(is_started=True)
    node = Node(host_name)
    tree._active_host_node[host_name] = node
    handler = LogHandler()

    with (
        patch("pyinfra_cli.log.routing.get_tree", return_value=tree),
        patch("pyinfra_cli.log.routing.attribute_host", return_value=(host_name, message)),
    ):
        if source == "log":
            handler.emit(logging.makeLogRecord({"msg": message, "levelno": logging.INFO}))
        else:
            echo(message, err=True)

        assert node.status == NodeStatus.RUNNING
        handler.emit(
            logging.makeLogRecord(
                {
                    "msg": "Success",
                    "levelno": logging.INFO,
                    "pyinfra_status_changed": True,
                    "pyinfra_status_text": "Success",
                }
            )
        )

    assert node.detail_lines == [DetailItem(text=message)]
    assert node.detail == "Success"
    assert node.status == NodeStatus.OK
