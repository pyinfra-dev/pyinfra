import re
from datetime import datetime
from pathlib import PurePosixPath
from unittest import TestCase
from unittest.mock import patch

from rich.console import Console

from pyinfra.api import Config, State

import pyinfra_cli.prints as prints_module
from pyinfra_cli.console import console
from pyinfra_cli.prints import (
    _display_width,
    _format_host_data,
    _scalar_style,
    print_inventory,
    print_rows,
)

from ..util import make_inventory


def _rows(*rows: list[str]) -> list[str]:
    output: list[str] = []
    print_rows([(output.append, row) for row in rows])
    return output


def test_display_width_counts_terminal_cells():
    assert _display_width("ascii") == 5
    # East Asian wide and fullwidth characters take two cells each
    assert _display_width("中文") == 4
    assert _display_width("ＡＢＣ") == 6
    # A skin tone modifier and a combining sound mark add no cells
    # (\u304b\u3099 is ka + combining voiced mark, the NFD form of ga)
    assert _display_width("👍🏽") == 2
    assert _display_width("\u304b\u3099") == 2
    # ANSI codes are not printed, so they take no cells
    assert _display_width("\033[1mhello\033[0m") == 5


def test_print_rows_ascii_table_is_unchanged():
    assert _rows(["Operation", "Hosts"], ["short", "1"]) == [
        "Operation   Hosts   ",
        "short       1       ",
    ]


def test_print_rows_pads_cjk_by_display_width():
    # The example from the issue: the CJK row must not push the next column
    # right of the header.
    assert _rows(["Operation", "Hosts"], ["随便输出一些中文试试", "1"]) == [
        "Operation" + " " * 14 + "Hosts   ",
        "随便输出一些中文试试" + " " * 3 + "1       ",
    ]


def test_print_rows_pads_coloured_cjk_in_a_later_column():
    green_ok = "\033[32m成功\033[0m"
    assert _rows(["Name", "Result", "Hosts"], ["a", green_ok, "1"], ["b", "ok", "2"]) == [
        "Name   Result   Hosts   ",
        "a      " + green_ok + " " * 5 + "1       ",
        "b      ok       2       ",
    ]


def test_print_rows_does_not_widen_zero_width_characters():
    # A skin tone modifier and a combining mark are drawn inside the
    # character before them, so they must not add padding.
    assert _rows(["Operation", "Hosts"], ["echo 👍🏽", "1"], ["\u304b\u3099", "2"]) == [
        "Operation   Hosts   ",
        "echo 👍🏽" + " " * 5 + "1       ",
        "\u304b\u3099" + " " * 10 + "2       ",
    ]


def _render_inventory(host_data: dict) -> str:
    inventory = make_inventory(hosts=(("somehost", host_data),))
    state = State(inventory, Config())
    # Use a wide, fixed-width console so the table is never truncated (the shared
    # console's width varies by platform/terminal, which would clip cell content).
    wide_console = Console(width=200, force_terminal=False, highlight=False)
    with patch.object(prints_module, "console", wide_console):
        with wide_console.capture() as capture:
            print_inventory(state)
    return capture.get()


class TestPrintInventory(TestCase):
    def test_scalars_render_as_flat_key_value_lines(self):
        output = _render_inventory({"role": "web", "port": 80, "enabled": True})

        assert "role: web" in output
        assert "port: 80" in output
        assert "enabled: True" in output
        # Scalars must NOT be dumped as JSON (no quoted keys/values).
        assert '"role"' not in output
        assert '"web"' not in output

    def test_nested_values_render_as_json(self):
        output = _render_inventory({"tags": ["a", "b"], "meta": {"cpu": 4}})

        # Header line for the key, then indented JSON for the value.
        assert "tags:" in output
        assert '"a"' in output and '"b"' in output
        assert "meta:" in output
        assert '"cpu": 4' in output

    def test_non_json_scalars_render_via_str(self):
        created = datetime(2021, 8, 14, 10, 30)
        # PurePosixPath keeps str() stable across platforms (WindowsPath would
        # render with backslashes).
        path = PurePosixPath("/opt/app")
        output = _render_inventory({"created": created, "path": path})

        assert f"created: {created}" in output
        assert f"path: {path}" in output

    def test_re_pattern_does_not_crash(self):
        # Regression: a compiled regex (as a nested dict key) previously crashed
        # the whole `debug-inventory` command trying to JSON-encode it.
        output = _render_inventory(
            {"fake_responses": {re.compile(r"^pip"): {"success": False}}},
        )

        assert "fake_responses:" in output
        assert "success" in output

    def test_empty_data(self):
        # `make_inventory` always injects some data, so exercise the helper
        # directly for the empty case.
        with console.capture() as capture:
            console.print(_format_host_data({}))
        assert "(no data)" in capture.get()

    def test_scalar_styling_matches_json_highlighter(self):
        # Scalars are coloured by type to match Rich's JSON highlighter.
        assert _scalar_style(True) == "json.bool_true"
        assert _scalar_style(False) == "json.bool_false"
        assert _scalar_style(None) == "json.null"
        assert _scalar_style(80) == "json.number"
        assert _scalar_style(1.5) == "json.number"
        assert _scalar_style("web") == "json.str"
        # Non-JSON scalars render unstyled (shown via str()).
        assert _scalar_style(datetime(2021, 8, 14)) == ""
        assert _scalar_style(PurePosixPath("/opt/app")) == ""
