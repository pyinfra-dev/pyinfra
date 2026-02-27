from __future__ import annotations

from pyinfra.api import Config, State
from pyinfra.api.connect import connect_all, disconnect_all

from ..util import make_inventory


def test_inventory_construction():
    inventory = make_inventory()

    assert len(inventory.hosts) == 2
    assert inventory.get_host("somehost") is not None
    assert inventory.get_host("anotherhost") is not None


def test_state_connect_cycle(fake_asyncssh):
    inventory = make_inventory()
    state = State(inventory, Config())

    connect_all(state)
    assert len(state.active_hosts) == 2

    disconnect_all(state)
    assert len(state.active_hosts) == 0
