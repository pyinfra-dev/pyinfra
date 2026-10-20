from unittest import TestCase
from unittest.mock import patch

from pyinfra.api import Inventory, connectors
from pyinfra.api.connectors import (
    get_connector,
    get_execution_connector,
    get_execution_connectors,
)
from pyinfra.api.exceptions import NoConnectorError

# Captured before any patch, so the fakes can be listed alongside the installed connectors.
_REAL_ENTRY_POINTS = connectors.entry_points


class FakeEntryPoint:
    def __init__(self, name, connector=None, error=None):
        self.name = name
        self.connector = connector
        self.error = error
        self.loaded = False

    def load(self):
        self.loaded = True
        if self.error:
            raise self.error
        return self.connector


def _broken(name="ghost"):
    return FakeEntryPoint(name, error=ImportError(f"No module named 'pyinfra.connectors.{name}'"))


def _entry_points_with(*fakes):
    """Patch entry_points so the given fakes are listed alongside the real connectors."""

    def _entry_points(group=None):
        return [*_REAL_ENTRY_POINTS(group=group), *fakes]

    return patch("pyinfra.api.connectors.entry_points", side_effect=_entry_points)


class TestConnectorLoading(TestCase):
    def test_an_unused_broken_connector_costs_nothing(self):
        """A connector nobody asks for is never imported, so it cannot break an inventory."""

        broken = _broken()

        with _entry_points_with(broken):
            inventory = Inventory((["@local"], {}))

        assert list(inventory.hosts) == ["@local"]
        assert broken.loaded is False

    def test_a_broken_connector_is_reported_when_requested(self):
        """Asking for it is an error naming both the connector and the cause."""

        with _entry_points_with(_broken()):
            with self.assertRaises(NoConnectorError) as context:
                get_connector("ghost")

        message = str(context.exception)
        assert "Invalid connector: ghost" in message
        assert "it is installed but could not be loaded" in message
        assert "No module named 'pyinfra.connectors.ghost'" in message

    def test_a_broken_connector_in_an_inventory_names_the_cause(self):
        """The same error, reached through the inventory rather than directly."""

        with _entry_points_with(_broken()):
            with self.assertRaises(NoConnectorError) as context:
                Inventory((["@ghost/somehost"], {}))

        assert "it is installed but could not be loaded" in str(context.exception)

    def test_an_unknown_connector_has_no_cause_to_report(self):
        with _entry_points_with():
            with self.assertRaises(NoConnectorError) as context:
                get_connector("nope")

        assert str(context.exception) == "Invalid connector: nope"

    def test_a_connector_that_cannot_execute_commands_is_reported(self):
        """An inventory-only connector gets a clear answer rather than a bare KeyError."""

        class InventoryOnly:
            handles_execution = False

        with _entry_points_with(FakeEntryPoint("names-only", connector=InventoryOnly)):
            with self.assertRaises(NoConnectorError) as context:
                get_execution_connector("names-only")

        assert "it cannot execute commands" in str(context.exception)

    def test_get_execution_connectors_keeps_only_the_ones_that_execute(self):
        """The eager lookup filters on ``handles_execution``, as it always has."""

        class InventoryOnly:
            handles_execution = False

        class Executes:
            handles_execution = True

        with _entry_points_with(
            FakeEntryPoint("names-only", connector=InventoryOnly),
            FakeEntryPoint("executes", connector=Executes),
        ):
            execution_connectors = get_execution_connectors()

        assert "names-only" not in execution_connectors
        assert execution_connectors["executes"] is Executes
        assert "ssh" in execution_connectors  # the installed connectors are there too

    def test_get_execution_connectors_still_reports_a_broken_connector(self):
        """It imports every connector, so a broken one fails here - as it always has."""

        with _entry_points_with(_broken()):
            with self.assertRaises(ImportError):
                get_execution_connectors()

    def test_the_default_connector_is_resolved_once_per_inventory(self):
        """A large inventory does not rescan the entry points for every host."""

        scans = []

        def _counting_entry_points(group=None):
            scans.append(group)
            return [*_REAL_ENTRY_POINTS(group=group)]

        with patch("pyinfra.api.connectors.entry_points", side_effect=_counting_entry_points):
            inventory = Inventory((["host1", "host2", "host3"], {}))

        assert list(inventory.hosts) == ["host1", "host2", "host3"]
        assert len(scans) == 1
