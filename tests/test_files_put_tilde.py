"""
Unit tests for tilde expansion in files.put() operation.
Tests for Issue #1235 - files.put() does not expand ~
"""

import os
from unittest import TestCase
from unittest.mock import patch

from pyinfra.operations import files

from .util import FakeState, create_host
from pyinfra.context import ctx_host, ctx_state


class TestFilesPutTildeExpansion(TestCase):
    """Test that files.put() expands tilde in dest parameter"""

    def setUp(self):
        self.state = FakeState()

    @patch("os.path.expanduser")
    def test_tilde_expansion_in_dest(self, mock_expanduser):
        """Test that tilde is expanded in dest parameter before processing"""

        # Mock expanduser to return a predictable path
        mock_expanduser.return_value = "/home/testuser/target.txt"

        # Create a host with appropriate facts
        host = create_host(
            self.state,
            facts={
                "files.File": {
                    "path=/home/testuser/target.txt": None,
                },
                "files.Directory": {
                    "path=/home/testuser": True,
                    "path=/home/testuser/target.txt": None,
                },
            },
        )

        # Create a temp file to use as src
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content\n")
            temp_file = f.name

        try:
            with ctx_state.use(self.state):
                with ctx_host.use(host):
                    # Call put with tilde in dest
                    list(
                        files.put._inner(
                            src=temp_file,
                            dest="~/target.txt",
                            add_deploy_dir=False,
                            create_remote_dir=False,
                        )
                    )

            # Verify expanduser was called with the tilde path
            mock_expanduser.assert_called_once_with("~/target.txt")

        finally:
            os.unlink(temp_file)

    @patch("os.path.expanduser")
    def test_tilde_expansion_prevents_literal_tilde_dir(self, mock_expanduser):
        """Test that expanding tilde prevents creation of literal ~ directory"""

        # Mock expanduser to return expanded path
        mock_expanduser.return_value = "/home/testuser/subdir/target.txt"

        # Create a host with appropriate facts
        host = create_host(
            self.state,
            facts={
                "files.File": {
                    "path=/home/testuser/subdir/target.txt": None,
                },
                "files.Directory": {
                    "path=/home/testuser": True,
                    "path=/home/testuser/subdir": None,  # Directory doesn't exist
                    "path=/home/testuser/subdir/target.txt": None,
                },
            },
        )

        # Create a temp file
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content\n")
            temp_file = f.name

        try:
            with ctx_state.use(self.state):
                with ctx_host.use(host):
                    # Call put with tilde in dest and create_remote_dir=True
                    commands = list(
                        files.put._inner(
                            src=temp_file,
                            dest="~/subdir/target.txt",
                            add_deploy_dir=False,
                            create_remote_dir=True,
                        )
                    )

            # Verify expanduser was called
            mock_expanduser.assert_called_once_with("~/subdir/target.txt")

            # Verify no command creates a literal ~ directory
            for cmd in commands:
                cmd_str = str(cmd)
                # Check that we don't have "mkdir ~" or similar
                if "mkdir" in cmd_str.lower():
                    # The mkdir command should NOT contain a bare tilde
                    self.assertNotIn(" ~", cmd_str, f"Found literal tilde in mkdir command: {cmd_str}")
                    self.assertNotIn(" ~/", cmd_str, f"Found unexpanded tilde path in mkdir: {cmd_str}")

        finally:
            os.unlink(temp_file)
