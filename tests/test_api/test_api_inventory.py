from unittest import TestCase

from pyinfra.api import Inventory


class TestInventoryApi(TestCase):
    def test_create_inventory(self):
        inventory = Inventory((["somehost", "anotherhost", "anotherotherhost"], {}))
        assert len(inventory) == 3

    def test_create_inventory_data(self):
        default_data = {"default_data": "default_data"}
        inventory = Inventory((["somehost"], default_data))
        assert inventory.get_data() == default_data
        assert inventory.get_host_data("somehost") == {}

    def test_create_inventory_host_data(self):
        default_data = {"default_data": "default_data", "host_data": "none"}
        somehost_data = {"host_data": "host_data"}

        inventory = Inventory(
            (
                [("somehost", somehost_data), "anotherhost"],
                default_data,
            ),
        )

        assert inventory.get_data() == default_data
        assert inventory.get_host_data("somehost") == somehost_data
        assert inventory.get_host_data("anotherhost") == {}
        assert inventory.get_host("anotherhost").data.host_data == "none"

    def test_create_inventory_override_data(self):
        default_data = {"default_data": "default_data", "override_data": "ignored"}
        override_data = {"override_data": "override_data"}
        somehost_data = {"host_data": "host_data"}

        inventory = Inventory(
            (
                [("somehost", somehost_data), "anotherhost"],
                default_data,
            ),
            override_data=override_data,
        )

        assert inventory.get_data() == default_data
        assert inventory.get_override_data() == override_data

        assert inventory.get_host("somehost").data.host_data == "host_data"
        assert inventory.get_host("anotherhost").data.get("host_data") is None

        assert inventory.get_host("somehost").data.override_data == "override_data"
        assert inventory.get_host("anotherhost").data.override_data == "override_data"
