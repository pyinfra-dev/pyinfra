"""
Tests for the @chain connector.
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from pyinfra.api.exceptions import ConnectError, InventoryError
from pyinfra.connectors.chain import ChainedConnector, _parse_chain

from ..util import make_inventory


class TestParseChain(TestCase):
    def test_two_levels(self):
        result = _parse_chain("@ssh/mydoodba/@docker/mycontainer")
        assert result == [("ssh", "mydoodba"), ("docker", "mycontainer")]

    def test_three_levels(self):
        result = _parse_chain("@ssh/host/@docker/container/@chroot/rootfs")
        assert result == [
            ("ssh", "host"),
            ("docker", "container"),
            ("chroot", "rootfs"),
        ]

    def test_arg_with_colon(self):
        # Docker image tags use colons — must not be confused with separators
        result = _parse_chain("@ssh/myhost/@docker/ubuntu:20.04")
        assert result == [("ssh", "myhost"), ("docker", "ubuntu:20.04")]

    def test_too_few_segments_raises(self):
        with self.assertRaises(InventoryError):
            _parse_chain("@ssh/host")  # no /@ separator

    def test_duplicate_connector_raises(self):
        with self.assertRaises(InventoryError) as ctx:
            _parse_chain("@ssh/bastion/@ssh/inner")
        assert "appears more than once" in str(ctx.exception)

    def test_malformed_segment_raises(self):
        with self.assertRaises(InventoryError):
            _parse_chain("not-at-sign/@docker/c")


class TestChainMakeNamesData(TestCase):
    def test_make_names_data_two_levels(self):
        with patch(
            "pyinfra.api.connectors.get_all_connectors",
        ) as mock_connectors:
            # Mock ssh connector
            ssh_cls = MagicMock()
            ssh_cls.make_names_data.return_value = iter(
                [("@ssh/host", {"ssh_hostname": "host"}, ["@ssh"])]
            )
            # Mock docker connector
            docker_cls = MagicMock()
            docker_cls.make_names_data.return_value = iter(
                [("@docker/mycontainer", {"docker_identifier": "mycontainer"}, ["@docker"])]
            )
            mock_connectors.return_value = {
                "ssh": ssh_cls,
                "docker": docker_cls,
            }

            results = list(ChainedConnector.make_names_data("@ssh/host/@docker/mycontainer"))

        assert len(results) == 1
        name, data, groups = results[0]
        assert name == "@ssh/host/@docker/mycontainer"
        assert data["ssh_hostname"] == "host"
        assert data["docker_identifier"] == "mycontainer"
        assert data["chain_segments"] == [("ssh", "host"), ("docker", "mycontainer")]
        assert "@chain" in groups
        assert "@ssh" in groups
        assert "@docker" in groups

    def test_make_names_data_no_name_raises(self):
        with self.assertRaises(InventoryError):
            list(ChainedConnector.make_names_data(None))

    def test_make_names_data_unknown_connector_raises(self):
        with patch(
            "pyinfra.api.connectors.get_all_connectors",
            return_value={},
        ):
            with self.assertRaises(InventoryError):
                list(ChainedConnector.make_names_data("@ssh/host/@unknown/foo"))


class TestChainInventory(TestCase):
    """Integration tests: chain detection in inventory parsing."""

    def test_chain_detected_in_inventory(self):
        inventory = make_inventory(hosts=("@ssh/mydoodba/@docker/mycontainer",))
        host = inventory.get_host("@ssh/mydoodba/@docker/mycontainer")
        assert host is not None
        # The connector class should be ChainedConnector
        assert host.connector_cls is ChainedConnector

    def test_no_chain_unchanged(self):
        """Ensure single-connector hosts still resolve to their original connector."""
        from pyinfra.connectors.ssh import SSHConnector

        inventory = make_inventory(hosts=("@ssh/somehost",))
        host = inventory.get_host("@ssh/somehost")
        assert host.connector_cls is SSHConnector


class TestChainWrapMethods(TestCase):
    """Unit tests for the wrap_* methods on inner connectors."""

    def test_docker_wrap_exec_command(self):
        from pyinfra.api import Config, State
        from pyinfra.connectors.docker import DockerConnector
        from pyinfra.api import StringCommand

        inventory = make_inventory(hosts=("@docker/mycontainer",))
        State(inventory, Config())
        host = inventory.get_host("@docker/mycontainer")

        connector = DockerConnector(host.state, host)
        cmd = StringCommand("ls", "/tmp")
        result = connector.wrap_exec_command(cmd, "mycontainer")
        raw = result.get_raw_value()
        assert "docker" in raw
        assert "exec" in raw
        assert "mycontainer" in raw

    def test_chroot_wrap_exec_command(self):
        from pyinfra.api import Config, State
        from pyinfra.connectors.chroot import ChrootConnector
        from pyinfra.api import StringCommand

        inventory = make_inventory(hosts=("@chroot/rootfs",))
        State(inventory, Config())
        host = inventory.get_host("@chroot/rootfs")

        connector = ChrootConnector(host.state, host)
        cmd = StringCommand("ls", "/etc")
        result = connector.wrap_exec_command(cmd, "/rootfs")
        raw = result.get_raw_value()
        assert "chroot" in raw
        assert "/rootfs" in raw

    def test_docker_wrap_copy_into(self):
        from pyinfra.api import Config, State
        from pyinfra.connectors.docker import DockerConnector

        inventory = make_inventory(hosts=("@docker/mycontainer",))
        State(inventory, Config())
        host = inventory.get_host("@docker/mycontainer")

        connector = DockerConnector(host.state, host)
        result = connector.wrap_copy_into("/tmp/staging.whl", "/tmp/foo.whl", "mycontainer")
        raw = result.get_raw_value()
        assert "docker" in raw
        assert "cp" in raw
        assert "mycontainer:/tmp/foo.whl" in raw

    def test_ssh_wrap_exec_raises(self):
        """SSH cannot be used as an inner connector."""
        from pyinfra.connectors.ssh import SSHConnector
        from pyinfra.api import Config, State
        from pyinfra.api import StringCommand

        inventory = make_inventory(hosts=("@ssh/somehost",))
        State(inventory, Config())
        host = inventory.get_host("@ssh/somehost")
        connector = SSHConnector.__new__(SSHConnector)
        connector.state = host.state
        connector.host = host
        cmd = StringCommand("ls")
        with self.assertRaises(NotImplementedError):
            connector.wrap_exec_command(cmd, "somehost")


class TestGetRuntimeId(TestCase):
    """Tests for get_runtime_id() on connectors."""

    def test_get_runtime_id_from_field(self):
        """Connector with runtime_id_field set reads from self.data."""
        from pyinfra.connectors.base import BaseConnector
        from pyinfra.api import Config, State

        class MockConnector(BaseConnector):
            runtime_id_field = "my_id"

            @staticmethod
            def make_names_data(name=None):
                raise NotImplementedError()

            def run_shell_command(self, *a, **kw):
                raise NotImplementedError()

            def put_file(self, *a, **kw):
                raise NotImplementedError()

            def get_file(self, *a, **kw):
                raise NotImplementedError()

        inventory = make_inventory(hosts=("@ssh/somehost",))
        state = State(inventory, Config())
        host = inventory.get_host("@ssh/somehost")
        connector = MockConnector.__new__(MockConnector)
        connector.state = state
        connector.host = host
        connector.data = {"my_id": "test-id"}
        assert connector.get_runtime_id() == "test-id"

    def test_get_runtime_id_not_implemented(self):
        """Connectors without runtime_id_field raise NotImplementedError."""
        from pyinfra.connectors.ssh import SSHConnector
        from pyinfra.api import Config, State

        inventory = make_inventory(hosts=("@ssh/somehost",))
        State(inventory, Config())
        host = inventory.get_host("@ssh/somehost")
        connector = SSHConnector.__new__(SSHConnector)
        connector.state = host.state
        connector.host = host
        # SSHConnector has no runtime_id_field
        with self.assertRaises(NotImplementedError):
            connector.get_runtime_id()


class TestRuntimeIdFor(TestCase):
    """Tests for ChainedConnector._runtime_id_for()."""

    def test_delegates_to_get_runtime_id(self):
        """_runtime_id_for calls connector.get_runtime_id()."""
        connector = MagicMock()
        connector.get_runtime_id.return_value = "runtime-42"

        chain = ChainedConnector.__new__(ChainedConnector)
        result = chain._runtime_id_for(connector, "fallback")
        assert result == "runtime-42"
        connector.get_runtime_id.assert_called_once()

    def test_falls_back_to_arg_string(self):
        """When get_runtime_id() raises NotImplementedError, use arg_string."""
        connector = MagicMock()
        connector.get_runtime_id.side_effect = NotImplementedError()

        chain = ChainedConnector.__new__(ChainedConnector)
        result = chain._runtime_id_for(connector, "fallback-id")
        assert result == "fallback-id"

    def test_no_runtime_id_and_no_arg_string_raises(self):
        """When both get_runtime_id() and arg_string are unavailable, raise ConnectError."""
        connector = MagicMock()
        connector.get_runtime_id.side_effect = NotImplementedError()

        chain = ChainedConnector.__new__(ChainedConnector)
        with self.assertRaises(ConnectError):
            chain._runtime_id_for(connector, None)
