from unittest import TestCase

from pyinfra import host, inventory
from pyinfra.api import Host, Inventory
from pyinfra.context import ctx_host, ctx_inventory


def _create_host():
    return Host(None, None, None, None)


class TestHostContextObject(TestCase):
    def test_context_host_dir_matches_class(self):
        assert dir(Host) == dir(host)

    def test_context_host_eq(self):
        host_obj = _create_host()
        ctx_host.set(host_obj)
        assert host == host_obj

    def test_context_host_repr(self):
        host_obj = _create_host()
        ctx_host.set(host_obj)
        assert repr(host) == "ContextObject(Host):Host(None)"

    def test_context_host_str(self):
        host_obj = _create_host()
        ctx_host.set(host_obj)
        assert str(host_obj) == "None"

    def test_context_host_attr(self):
        host_obj = _create_host()
        ctx_host.set(host_obj)

        with self.assertRaises(AttributeError):
            host_obj.hello

        setattr(host, "hello", "world")
        assert host_obj.hello == host.hello

    def test_context_host_class_attr(self):
        host_obj = _create_host()
        ctx_host.set(host_obj)
        assert ctx_host.isset() is True

        with self.assertRaises(AttributeError):
            host_obj.hello

        setattr(Host, "hello", "class_world")
        setattr(host_obj, "hello", "instance_world")

        assert host.hello == host.hello

        # Reset and check fallback to class variable
        ctx_host.reset()
        assert ctx_host.isset() is False
        assert host.hello == "class_world"


class TestInventoryContextObject(TestCase):
    def test_context_inventory_len(self):
        inventory_obj = Inventory(("host", "anotherhost"))
        ctx_inventory.set(inventory_obj)
        assert ctx_inventory.isset() is True

        assert len(inventory) == len(inventory_obj)

    def test_context_inventory_iter(self):
        inventory_obj = Inventory(("host", "anotherhost"))
        ctx_inventory.set(inventory_obj)
        assert ctx_inventory.isset() is True

        assert list(iter(inventory)) == list(iter(inventory_obj))
