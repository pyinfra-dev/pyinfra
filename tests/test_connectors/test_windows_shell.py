from unittest.mock import patch

from pyinfra.api import Config, State, StringCommand
from pyinfra.connectors.util import CommandOutput

from ..util import make_inventory


async def _fake_run_local_process_async(*args, **kwargs):
    return 0, CommandOutput([])


def test_cmd_connector_wraps_command():
    inventory = make_inventory(hosts=("@cmd",))
    state = State(inventory, Config())
    host = inventory.get_host("@cmd")

    with patch(
        "pyinfra.connectors.cmd.run_local_process_async",
        side_effect=_fake_run_local_process_async,
    ) as run_local_process:
        host.run_shell_command(StringCommand("echo", "hello"))

    called_command = run_local_process.await_args.args[0]
    assert called_command.startswith('cmd /C "')


def test_powershell_connector_wraps_command():
    inventory = make_inventory(hosts=("@powershell",))
    state = State(inventory, Config())
    host = inventory.get_host("@powershell")

    with patch(
        "pyinfra.connectors.powershell.run_local_process_async",
        side_effect=_fake_run_local_process_async,
    ) as run_local_process:
        host.run_shell_command(StringCommand("Get-Process"))

    called_command = run_local_process.await_args.args[0]
    assert called_command.startswith("powershell -NoProfile -NonInteractive")
