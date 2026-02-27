from __future__ import annotations

from pyinfra.api import Config, State
from pyinfra.api.connect import connect_all, disconnect_all
from pyinfra.api.facts import get_facts
from pyinfra.facts.server import Command

from ..util import make_inventory


def test_get_facts_runs_commands(fake_asyncssh):
    inventory = make_inventory()
    state = State(inventory, Config())

    connect_all(state)

    for connection in fake_asyncssh.values():
        connection.command_results["echo fact"] = {
            "stdout": "value\n",
            "stderr": "",
            "exit_status": 0,
        }

    result = get_facts(state, Command, ("echo fact",))

    for host, value in result.items():
        assert value == "value"

    disconnect_all(state)
