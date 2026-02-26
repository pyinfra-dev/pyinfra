from unittest import TestCase
from unittest.mock import AsyncMock, patch

from pyinfra.api import Config, QuoteString, State, StringCommand
from pyinfra.api.connect import connect_all
from pyinfra.connectors.util import CommandOutput, make_unix_command

from ..util import make_inventory


class TestKubectlConnector(TestCase):
    def setUp(self):
        self.local_connect_patch = patch(
            "pyinfra.connectors.kubectl.LocalConnector.connect",
            new_callable=AsyncMock,
        )
        self.local_connect = self.local_connect_patch.start()

        self.local_run_shell_patch = patch(
            "pyinfra.connectors.kubectl.LocalConnector.run_shell_command",
            new_callable=AsyncMock,
        )
        self.local_run_shell = self.local_run_shell_patch.start()
        self.local_run_shell.return_value = (True, CommandOutput([]))

    def tearDown(self):
        self.local_run_shell_patch.stop()
        self.local_connect_patch.stop()

    def test_connect_all(self):
        inventory = make_inventory(hosts=("@kubectl/default/nginx:app",))
        state = State(inventory, Config())
        connect_all(state)

        assert len(state.active_hosts) == 1

    def test_run_shell_command(self):
        inventory = make_inventory(hosts=("@kubectl/default/nginx",))
        State(inventory, Config())
        host = inventory.get_host("@kubectl/default/nginx")
        host.connect()

        self.local_run_shell.return_value = (True, CommandOutput([]))
        output = host.run_shell_command("echo hi", _stdin="input-data", _get_pty=True)

        assert output[0] is True

        unix_command = make_unix_command("echo hi").get_raw_value()
        expected = StringCommand(
            "kubectl",
            "-n",
            "default",
            "exec",
            "nginx",
            "--",
            "sh",
            "-c",
            QuoteString(unix_command),
        )
        call = self.local_run_shell.await_args_list[-1]
        called_command = call.args[0]
        assert called_command.get_raw_value() == expected.get_raw_value()
