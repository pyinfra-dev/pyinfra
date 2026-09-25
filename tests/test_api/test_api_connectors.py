from unittest import TestCase
from unittest.mock import patch

from pyinfra.api import connectors
from pyinfra.api.connectors import (
    get_all_connectors,
    get_execution_connector,
    get_execution_connectors,
    invalid_connector_error,
)
from pyinfra.api.exceptions import NoConnectorError


class FakeEntryPoint:
    def __init__(self, name, connector=None, error=None):
        self.name = name
        self.connector = connector
        self.error = error

    def load(self):
        if self.error:
            raise self.error
        return self.connector


class TestConnectorLoading(TestCase):
    def setUp(self):
        # Broken connectors are only reported once per process, so reset between tests.
        connectors._reported_broken_connectors.clear()

    def test_broken_entry_point_is_skipped_with_a_warning(self):
        """
        A connector whose module cannot be imported must not break every other connector.

        This happens with stale metadata: uninstalling a package that ships a connector, or
        an editable install recording entry points from another branch.
        """

        broken = FakeEntryPoint(
            "ghost",
            error=ImportError("No module named 'pyinfra.connectors.ghost'"),
        )
        working = FakeEntryPoint("working", connector="the-connector")

        with patch("pyinfra.api.connectors.entry_points", return_value=[broken, working]):
            with self.assertLogs("pyinfra", level="WARNING") as logs:
                connectors = get_all_connectors()

        assert connectors == {"working": "the-connector"}
        assert len(logs.output) == 1
        assert "ghost" in logs.output[0]
        assert "No module named 'pyinfra.connectors.ghost'" in logs.output[0]

    def test_requesting_a_broken_connector_explains_the_cause(self):
        """Skipping a broken connector must not hide *why* it is unavailable when asked for."""

        broken = FakeEntryPoint(
            "ghost",
            error=ImportError("No module named 'pyinfra.connectors.ghost'"),
        )

        with patch("pyinfra.api.connectors.entry_points", return_value=[broken]):
            with self.assertRaises(NoConnectorError) as context:
                get_execution_connector("ghost")

        message = str(context.exception)
        assert "Invalid connector: ghost" in message
        assert "No module named 'pyinfra.connectors.ghost'" in message

    def test_requesting_an_unknown_connector_has_no_cause_to_report(self):
        with patch("pyinfra.api.connectors.entry_points", return_value=[]):
            error = invalid_connector_error("nope")

        assert str(error) == "Invalid connector: nope"

    def test_execution_connectors_skip_broken_entry_points(self):
        class WorkingConnector:
            handles_execution = True

        class InventoryConnector:
            handles_execution = False

        entry_points = [
            FakeEntryPoint("ghost", error=ImportError("broken")),
            FakeEntryPoint("working", connector=WorkingConnector),
            FakeEntryPoint("inventory", connector=InventoryConnector),
        ]

        with patch("pyinfra.api.connectors.entry_points", return_value=entry_points):
            with self.assertLogs("pyinfra", level="WARNING"):
                connectors = get_execution_connectors()

        assert connectors == {"working": WorkingConnector}
