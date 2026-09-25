import re
from datetime import datetime
from pathlib import PurePosixPath
from unittest import TestCase
from unittest.mock import patch

from rich.console import Console

from pyinfra.api import Config, State

import pyinfra_cli.prints as prints_module
from pyinfra_cli.console import console
from pyinfra_cli.prints import _format_host_data, _scalar_style, print_inventory

from ..util import make_inventory


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
