from unittest import TestCase

from pyinfra.api.host import HostData


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
