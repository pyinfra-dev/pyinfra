from typing import cast
from unittest.mock import MagicMock, patch

from pyinfra.api import Config, State
from pyinfra.api.arguments import CONNECTOR_ARGUMENT_KEYS, AllArguments, pop_global_arguments
from pyinfra.api.connect import connect_all
from pyinfra.api.exceptions import PyinfraError
from pyinfra.api.facts import get_facts
from pyinfra.connectors.util import CommandOutput, OutputLine
from pyinfra.context import ctx_host, ctx_state
from pyinfra.facts.server import Arch, Command

from ..paramiko_util import PatchSSHTestCase
from ..util import make_inventory


def _get_executor_defaults(state, host):
    with ctx_state.use(state):
        with ctx_host.use(host):
            global_argument_defaults, _ = pop_global_arguments(state, host, {})
    return {
        key: value
        for key, value in global_argument_defaults.items()
        if key in CONNECTOR_ARGUMENT_KEYS
    }


class TestFactsApi(PatchSSHTestCase):
    def test_get_fact(self):
        inventory = make_inventory(hosts=("anotherhost",))
        state = State(inventory, Config())

        anotherhost = inventory.get_host("anotherhost")

        connect_all(state)

        with patch("pyinfra.connectors.ssh.SSHConnector.run_shell_command") as fake_run_command:
            fake_run_command.return_value = True, CommandOutput(
                [OutputLine("stdout", "some-output")]
            )
            fact_data = get_facts(state, Command, ("yes",))

        assert fact_data == {anotherhost: "some-output"}

        fake_run_command.assert_called_with(
            "yes",
            print_input=False,
            print_output=False,
            **_get_executor_defaults(state, anotherhost),
        )

    def test_get_fact_current_op_global_arguments(self):
        inventory = make_inventory(hosts=("anotherhost",))
        state = State(inventory, Config())

        anotherhost = inventory.get_host("anotherhost")

        connect_all(state)
        anotherhost.current_op_global_arguments = cast(
            AllArguments,
            {
                "_sudo": True,
                "_sudo_user": "someuser",
                "_su_user": "someuser",
                "_timeout": 10,
                "_env": {"HELLO": "WORLD"},
            },
        )

        with patch("pyinfra.connectors.ssh.SSHConnector.run_shell_command") as fake_run_command:
            fake_run_command.return_value = True, CommandOutput(
                [OutputLine("stdout", "some-output")]
            )
            fact_data = get_facts(state, Command, ("yes",))

        assert fact_data == {anotherhost: "some-output"}

        defaults = _get_executor_defaults(state, anotherhost)
        defaults.update(anotherhost.current_op_global_arguments)

        fake_run_command.assert_called_with(
            "yes",
            print_input=False,
            print_output=False,
            **defaults,
        )

    def test_get_fact_error(self):
        inventory = make_inventory(hosts=("anotherhost",))
        state = State(inventory, Config())

        anotherhost = inventory.get_host("anotherhost")

        connect_all(state)

        with patch("pyinfra.connectors.ssh.SSHConnector.run_shell_command") as fake_run_command:
            fake_run_command.return_value = False, MagicMock()

            with self.assertRaises(PyinfraError) as context:
                get_facts(state, Command, ("fail command",))

        assert context.exception.args[0] == "No hosts remaining!"

        fake_run_command.assert_called_with(
            "fail command",
            print_input=False,
            print_output=False,
            **_get_executor_defaults(state, anotherhost),
        )

    def test_get_fact_error_ignore(self):
        inventory = make_inventory(hosts=("anotherhost",))
        state = State(inventory, Config())

        anotherhost = inventory.get_host("anotherhost")

        connect_all(state)
        anotherhost.in_op = True
        anotherhost.current_op_global_arguments = cast(
            AllArguments,
            {
                "_ignore_errors": True,
            },
        )

        with patch("pyinfra.connectors.ssh.SSHConnector.run_shell_command") as fake_run_command:
            fake_run_command.return_value = False, MagicMock()
            fact_data = get_facts(state, Command, ("fail command",))

        assert fact_data == {anotherhost: None}

        fake_run_command.assert_called_with(
            "fail command",
            print_input=False,
            print_output=False,
            **_get_executor_defaults(state, anotherhost),
        )

    def test_get_fact_executor_override_arguments(self):
        inventory = make_inventory(hosts=("anotherhost",))
        state = State(inventory, Config())

        anotherhost = inventory.get_host("anotherhost")

        connect_all(state)

        with patch("pyinfra.connectors.ssh.SSHConnector.run_shell_command") as fake_run_command:
            fake_run_command.return_value = MagicMock(), CommandOutput(
                [OutputLine("stdout", "some-output")]
            )
            fact_data = get_facts(state, Command, ("yes",), {"_sudo": True})

        assert fact_data == {anotherhost: "some-output"}

        defaults = _get_executor_defaults(state, anotherhost)
        defaults["_sudo"] = True

        fake_run_command.assert_called_with(
            "yes",
            print_input=False,
            print_output=False,
            **defaults,
        )

    def test_get_fact_executor_host_data_arguments(self):
        inventory = make_inventory(hosts=("anotherhost",))
        state = State(inventory, Config())

        anotherhost = inventory.get_host("anotherhost")
        anotherhost.data._sudo = True

        connect_all(state)

        with patch("pyinfra.connectors.ssh.SSHConnector.run_shell_command") as fake_run_command:
            fake_run_command.return_value = True, CommandOutput(
                [OutputLine("stdout", "some-output")]
            )
            fact_data = get_facts(state, Command, ("yes",))

        assert fact_data == {anotherhost: "some-output"}

        defaults = _get_executor_defaults(state, anotherhost)
        defaults["_sudo"] = True

        fake_run_command.assert_called_with(
            "yes",
            print_input=False,
            print_output=False,
            **defaults,
        )

    def test_get_fact_executor_mixed_arguments(self):
        inventory = make_inventory(hosts=("anotherhost",))
        state = State(inventory, Config())

        anotherhost = inventory.get_host("anotherhost")
        anotherhost.data._sudo = True
        anotherhost.data._sudo_user = "this-should-be-overridden"
        anotherhost.data._su_user = "this-should-be-overridden"

        anotherhost.current_op_global_arguments = cast(
            AllArguments,
            {
                "_su_user": "override-su-user",
            },
        )

        connect_all(state)

        with patch("pyinfra.connectors.ssh.SSHConnector.run_shell_command") as fake_run_command:
            fake_run_command.return_value = True, CommandOutput(
                [OutputLine("stdout", "some-output")]
            )
            fact_data = get_facts(
                state,
                Command,
                args=("yes",),
                kwargs={"_sudo_user": "override-sudo-user"},
            )

        assert fact_data == {anotherhost: "some-output"}

        defaults = _get_executor_defaults(state, anotherhost)
        defaults["_sudo"] = True
        defaults["_sudo_user"] = "override-sudo-user"
        defaults["_su_user"] = "override-su-user"

        fake_run_command.assert_called_with(
            "yes",
            print_input=False,
            print_output=False,
            **defaults,
        )

    def test_get_fact_no_args(self):
        inventory = make_inventory(hosts=("host-1",))
        state = State(inventory, Config())

        connect_all(state)

        host_1 = inventory.get_host("host-1")
        defaults = _get_executor_defaults(state, host_1)

        with patch("pyinfra.connectors.ssh.SSHConnector.run_shell_command") as fake_run_command:
            fake_run_command.return_value = MagicMock(), CommandOutput(
                [OutputLine("stdout", "some-output")]
            )
            fact_data = get_facts(state, Arch)

        assert fact_data == {host_1: "some-output"}
        fake_run_command.assert_called_with(
            Arch().command(),
            print_input=False,
            print_output=False,
            **defaults,
        )


class TestHostFactsApi(PatchSSHTestCase):
    def test_get_host_fact(self):
        inventory = make_inventory(hosts=("host-1",))
        state = State(inventory, Config())

        connect_all(state)

        host_1 = inventory.get_host("host-1")
        defaults = _get_executor_defaults(state, host_1)

        with patch("pyinfra.connectors.ssh.SSHConnector.run_shell_command") as fake_run_command:
            fake_run_command.return_value = MagicMock(), CommandOutput(
                [OutputLine("stdout", "some-output")]
            )
            fact_data = host_1.get_fact(Command, command="echo hello world")

        assert fact_data == "some-output"
        fake_run_command.assert_called_with(
            "echo hello world",
            print_input=False,
            print_output=False,
            **defaults,
        )

    def test_get_host_fact_sudo(self):
        inventory = make_inventory(hosts=("host-1",))
        state = State(inventory, Config())

        connect_all(state)

        host_1 = inventory.get_host("host-1")
        defaults = _get_executor_defaults(state, host_1)
        defaults["_sudo"] = True

        with patch("pyinfra.connectors.ssh.SSHConnector.run_shell_command") as fake_run_command:
            fake_run_command.return_value = MagicMock(), CommandOutput(
                [OutputLine("stdout", "some-output")]
            )
            fact_data = host_1.get_fact(Command, command="echo hello world", _sudo=True)

        assert fact_data == "some-output"
        fake_run_command.assert_called_with(
            "echo hello world",
            print_input=False,
            print_output=False,
            **defaults,
        )

    def test_get_host_fact_sudo_no_args(self):
        inventory = make_inventory(hosts=("host-1",))
        state = State(inventory, Config())

        connect_all(state)

        host_1 = inventory.get_host("host-1")
        defaults = _get_executor_defaults(state, host_1)
        defaults["_sudo"] = True

        with patch("pyinfra.connectors.ssh.SSHConnector.run_shell_command") as fake_run_command:
            fake_run_command.return_value = MagicMock(), CommandOutput(
                [OutputLine("stdout", "some-output")]
            )
            fact_data = host_1.get_fact(Arch, _sudo=True)

        assert fact_data == "some-output"
        fake_run_command.assert_called_with(
            Arch().command(),
            print_input=False,
            print_output=False,
            **defaults,
        )
