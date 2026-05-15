from unittest import TestCase

from pyinfra.api import Config, State
from pyinfra.api.host import HostData

from ..util import make_inventory


class TestHostData(TestCase):
    def test_host_data(self):
        data = HostData("somehost", {"hello": "world"})
        assert data.hello == "world"
        assert data.get("hello") == "world"

    def test_host_data_multiple(self):
        data = HostData(
            "somehost",
            {"hello": "world"},
            {"hello": "not-world", "another": "thing"},
        )
        assert data.hello == "world"
        assert data.get("hello") == "world"
        assert data.another == "thing"

    def test_host_data_override(self):
        data = HostData("somehost", {"hello": "world"})
        assert data.hello == "world"

        data.hello = "override-world"
        assert data.hello == "override-world"

    def test_host_data_missing(self):
        data = HostData("somehost", {"hello": "world"})

        with self.assertRaises(AttributeError) as context:
            getattr(data, "not-a-key")

        assert context.exception.args[0] == "Host `somehost` has no data `not-a-key`"
        assert data.get("not-a-key") is None


class TestHostDeployContext(TestCase):
    def _make_host(self):
        inventory = make_inventory()
        State(inventory, Config())
        return inventory.get_host("somehost")

    def test_deploy_restores_state_after_exception(self):
        host = self._make_host()

        assert host.current_deploy_name is None
        assert host.in_deploy is False

        with self.assertRaises(RuntimeError):
            with host.deploy("failing.py", None, None, in_deploy=False):
                raise RuntimeError("boom")

        assert host.current_deploy_name is None
        assert host.current_deploy_kwargs is None
        assert host.current_deploy_data is None
        assert host.in_deploy is False

    def test_nested_deploy_restores_outer_name_after_exception(self):
        host = self._make_host()

        with host.deploy("outer", None, None, in_deploy=False):
            assert host.current_deploy_name == "outer"

            with self.assertRaises(ValueError):
                with host.deploy("inner", None, None, in_deploy=False):
                    assert host.current_deploy_name == "outer | inner"
                    raise ValueError("nope")

            assert host.current_deploy_name == "outer"

        assert host.current_deploy_name is None
