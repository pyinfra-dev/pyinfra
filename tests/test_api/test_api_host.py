from unittest import TestCase

import asyncio
from types import SimpleNamespace
from unittest.mock import patch

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


class TestHostDisconnect(TestCase):
    def test_disconnect_removes_askpass_before_connector_close(self):
        state = State(make_inventory(), Config())
        host = state.inventory.get_host("somehost")
        host.connector_data["sudo_askpass_path"] = "/tmp/askpass"

        calls: list[str] = []

        async def fake_remove(_host):
            calls.append("remove")

        async def fake_disconnect():
            calls.append("disconnect")

        host.connector = SimpleNamespace(disconnect=fake_disconnect)

        with patch("pyinfra.api.host.remove_any_sudo_askpass_file_async", fake_remove):
            asyncio.run(host.disconnect_async())

        assert calls == ["remove", "disconnect"]
