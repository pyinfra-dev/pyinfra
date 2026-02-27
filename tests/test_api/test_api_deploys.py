from __future__ import annotations

from pyinfra.api import Config, State
from pyinfra.api.connect import connect_all, disconnect_all
from pyinfra.api.deploy import add_deploy, deploy
from pyinfra.api.operations import run_ops
from pyinfra.operations import server

from ..util import make_inventory


@deploy()
def _sample_deploy():
    server.shell("echo deploy")


def test_deploy_runs_commands(fake_asyncssh):
    inventory = make_inventory()
    state = State(inventory, Config())

    connect_all(state)
    add_deploy(state, _sample_deploy)
    run_ops(state)

    for connection in fake_asyncssh.values():
        assert any("echo deploy" in command for command in connection.commands_run)

    disconnect_all(state)
