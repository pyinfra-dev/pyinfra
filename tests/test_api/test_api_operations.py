from __future__ import annotations

from pyinfra.api import BaseStateCallback, Config, State, StringCommand
from pyinfra.api.connect import connect_all, disconnect_all
from pyinfra.api.operation import add_op
from pyinfra.api.operations import run_ops
from pyinfra.operations import server

from ..util import make_inventory


class _TrackingCallback(BaseStateCallback):
    def __init__(self) -> None:
        self.started = []
        self.completed = []

    def operation_start(self, state: State, op_hash):
        self.started.append(op_hash)

    def operation_end(self, state: State, op_hash):
        self.completed.append(op_hash)


def test_run_ops_executes_commands(fake_asyncssh):
    inventory = make_inventory()
    state = State(inventory, Config())
    callback = _TrackingCallback()
    state.add_callback_handler(callback)

    connect_all(state)
    add_op(state, server.shell, "echo op-test")
    run_ops(state)

    assert callback.started
    assert callback.completed == callback.started

    for connection in fake_asyncssh.values():
        assert any("echo op-test" in command for command in connection.commands_run)

    disconnect_all(state)


def test_run_shell_command_with_custom_string_command(fake_asyncssh):
    inventory = make_inventory()
    state = State(inventory, Config())

    connect_all(state)
    host = inventory.get_host("somehost")
    connection = fake_asyncssh[host.name]
    connection.command_results["custom command"] = {
        "stdout": "done\n",
        "stderr": "",
        "exit_status": 0,
    }

    status, output = host.run_shell_command(StringCommand("custom", "command"))

    assert status is True
    assert output.stdout == "done"

    disconnect_all(state)
