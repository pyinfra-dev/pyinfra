from unittest import TestCase

from pyinfra import pseudo_host, pseudo_inventory
from pyinfra.api import Host, Inventory


def _create_host():
    return Host(None, None, None, None)


class TestPseudoHost(TestCase):
    def test_pseudo_host_dir_matches_class(self):
        assert dir(Host) == dir(pseudo_host)

    def test_pseudo_host_eq(self):
        host = _create_host()
        pseudo_host.set(host)
        assert host == pseudo_host

    def test_pseudo_host_repr(self):
        host = _create_host()
        pseudo_host.set(host)
        assert repr(pseudo_host) == 'PseudoModule(Host):Host(None)'

    def test_pseudo_host_str(self):
        host = _create_host()
        pseudo_host.set(host)
        assert str(pseudo_host) == 'None'

    def test_pseudo_host_attr(self):
        host = _create_host()
        pseudo_host.set(host)

        with self.assertRaises(AttributeError):
            host.hello

        setattr(host, 'hello', 'world')
        assert pseudo_host.hello == host.hello

    def test_pseudo_host_class_attr(self):
        host = _create_host()
        pseudo_host.set(host)
        assert pseudo_host.isset() is True

        with self.assertRaises(AttributeError):
            host.hello

        setattr(Host, 'hello', 'class_world')
        setattr(host, 'hello', 'instance_world')

        assert pseudo_host.hello == host.hello

        # Reset and check fallback to class variable
        pseudo_host.reset()
        assert pseudo_host.isset() is False
        assert pseudo_host.hello == 'class_world'


class TestPseudoInventory(TestCase):
    def test_pseudo_inventory_len(self):
        inventory = Inventory(('host', 'anotherhost'))
        pseudo_inventory.set(inventory)
        assert pseudo_inventory.isset() is True

        assert len(pseudo_inventory) == len(inventory)

    def test_pseudo_inventory_iter(self):
        inventory = Inventory(('host', 'anotherhost'))
        pseudo_inventory.set(inventory)
        assert pseudo_inventory.isset() is True

        assert list(iter(pseudo_inventory)) == list(iter(inventory))
