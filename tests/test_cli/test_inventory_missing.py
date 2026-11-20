"""
Regression tests for GH #2087: missing inventory file should raise a clear
CliError instead of a full traceback with UnicodeEncodeError.
"""

from unittest import TestCase

from pyinfra.context import ctx_inventory, ctx_state
from pyinfra_cli.exceptions import CliError
from pyinfra_cli.inventory import make_inventory, _resolves_to_host


class TestInventoryMissingFile(TestCase):
    def setUp(self):
        ctx_state.reset()
        ctx_inventory.reset()

    def test_resolves_to_host_rejects_path_like_strings(self):
        """
        Path-like strings containing '.' should not crash _resolves_to_host
        with UnicodeEncodeError when passed to socket.getaddrinfo.
        """
        assert _resolves_to_host("../some-dir/inventory") is False
        assert _resolves_to_host("./hidden-file") is False
        assert _resolves_to_host("/nonexistent/path.py") is False

    def test_make_inventory_missing_relative_path_raises_cli_error(self):
        """Relative path with '/' that doesn't exist should raise CliError."""
        with self.assertRaises(CliError) as cm:
            make_inventory("../some-dir/inventory")
        assert "Inventory file not found" in str(cm.exception)

    def test_make_inventory_missing_absolute_path_raises_cli_error(self):
        """Absolute path with '/' that doesn't exist should raise CliError."""
        with self.assertRaises(CliError) as cm:
            make_inventory("/nonexistent/path.py")
        assert "Inventory file not found" in str(cm.exception)

    def test_make_inventory_missing_dot_prefixed_path_raises_cli_error(self):
        """Dot-prefixed path that doesn't exist should raise CliError."""
        with self.assertRaises(CliError) as cm:
            make_inventory(".hidden-file")
        assert "Inventory file not found" in str(cm.exception)
