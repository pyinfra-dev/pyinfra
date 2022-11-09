from unittest.mock import MagicMock, patch

from pyinfra.api import Config, State
from pyinfra.api.arguments import get_executor_kwarg_keys, pop_global_arguments
from pyinfra.api.connect import connect_all
from pyinfra.api.exceptions import PyinfraError
from pyinfra.api.facts import get_facts
from pyinfra.facts.server import Arch, Command

from ..paramiko_util import PatchSSHTestCase
from ..util import make_inventory


def _get_executor_defaults(state, host):
    global_argument_defaults, _ = pop_global_arguments({}, state=state, host=host)
    return {
        key: value
        for key, value in global_argument_defaults.items()
        if key in get_executor_kwarg_keys()
    }


class TestFactsApi(PatchSSHTestCase):
    def test_get_fact(self):
        inventory = make_inventory(hosts=("anotherhost",))
        state = State(inventory, Config())

        anotherhost = inventory.get_host("anotherhost")

        connect_all(state)

        with patch("pyinfra.connectors.ssh.run_shell_command") as fake_run_command:
            fake_run_command.return_value = MagicMock(), [("stdout", "some-output")]
            fact_data = get_facts(state, Command, ("yes",))

        assert fact_data == {anotherhost: "some-output"}

        fake_run_command.assert_called_with(
            state,
            anotherhost,
            "yes",
            print_input=False,
            print_output=False,
            return_combined_output=True,
            **_get_executor_defaults(state, anotherhost),
        )

    def test_get_fact_current_op_global_arguments(self):
        inventory = make_inventory(hosts=("anotherhost",))
        state = State(inventory, Config())

        anotherhost = inventory.get_host("anotherhost")

        connect_all(state)
        anotherhost.current_op_global_kwargs = {
            "sudo": True,
            "sudo_user": "someuser",
            "use_sudo_password": True,
            "su_user": "someuser",
            "timeout": 10,
            "env": {"HELLO": "WORLD"},
        }

        with patch("pyinfra.connectors.ssh.run_shell_command") as fake_run_command:
            fake_run_command.return_value = MagicMock(), [("stdout", "some-output")]
            fact_data = get_facts(state, Command, ("yes",))

        assert fact_data == {anotherhost: "some-output"}

        defaults = _get_executor_defaults(state, anotherhost)
        defaults.update(anotherhost.current_op_global_kwargs)

        fake_run_command.assert_called_with(
            state,
            anotherhost,
            "yes",
            print_input=False,
            print_output=False,
            return_combined_output=True,
            **defaults,
        )

    def test_get_fact_error(self):
        inventory = make_inventory(hosts=("anotherhost",))
        state = State(inventory, Config())

        anotherhost = inventory.get_host("anotherhost")

        connect_all(state)

        with patch("pyinfra.connectors.ssh.run_shell_command") as fake_run_command:
            fake_run_command.return_value = False, MagicMock()

            with self.assertRaises(PyinfraError) as context:
                get_facts(state, Command, ("fail command",))

        assert context.exception.args[0] == "No hosts remaining!"

        fake_run_command.assert_called_with(
            state,
            anotherhost,
            "fail command",
            print_input=False,
            print_output=False,
            return_combined_output=True,
            **_get_executor_defaults(state, anotherhost),
        )

    def test_get_fact_error_ignore(self):
        inventory = make_inventory(hosts=("anotherhost",))
        state = State(inventory, Config())

        anotherhost = inventory.get_host("anotherhost")

        connect_all(state)
        anotherhost.current_op_global_kwargs = {
            "ignore_errors": True,
        }

        with patch("pyinfra.connectors.ssh.run_shell_command") as fake_run_command:
            fake_run_command.return_value = False, MagicMock()
            fact_data = get_facts(state, Command, ("fail command",))

        assert fact_data == {anotherhost: None}

        fake_run_command.assert_called_with(
            state,
            anotherhost,
            "fail command",
            print_input=False,
            print_output=False,
            return_combined_output=True,
            **_get_executor_defaults(state, anotherhost),
        )

    def test_get_fact_executor_override_arguments(self):
        inventory = make_inventory(hosts=("anotherhost",))
        state = State(inventory, Config())

        anotherhost = inventory.get_host("anotherhost")

        connect_all(state)

        with patch("pyinfra.connectors.ssh.run_shell_command") as fake_run_command:
            fake_run_command.return_value = MagicMock(), [("stdout", "some-output")]
            fact_data = get_facts(state, Command, ("yes",), {"_sudo": True})

        assert fact_data == {anotherhost: "some-output"}

        defaults = _get_executor_defaults(state, anotherhost)
        defaults["sudo"] = True

        fake_run_command.assert_called_with(
            state,
            anotherhost,
            "yes",
            print_input=False,
            print_output=False,
            return_combined_output=True,
            **defaults,
        )

    def test_get_fact_executor_host_data_arguments(self):
        inventory = make_inventory(hosts=("anotherhost",))
        state = State(inventory, Config())

        anotherhost = inventory.get_host("anotherhost")
        anotherhost.data._sudo = True

        connect_all(state)

        with patch("pyinfra.connectors.ssh.run_shell_command") as fake_run_command:
            fake_run_command.return_value = MagicMock(), [("stdout", "some-output")]
            fact_data = get_facts(state, Command, ("yes",))

        assert fact_data == {anotherhost: "some-output"}

        defaults = _get_executor_defaults(state, anotherhost)
        defaults["sudo"] = True

        fake_run_command.assert_called_with(
            state,
            anotherhost,
            "yes",
            print_input=False,
            print_output=False,
            return_combined_output=True,
            **defaults,
        )

    def test_get_fact_executor_mixed_arguments(self):
        inventory = make_inventory(hosts=("anotherhost",))
        state = State(inventory, Config())

        anotherhost = inventory.get_host("anotherhost")
        anotherhost.data._sudo = True
        anotherhost.data._sudo_user = "this-should-be-overridden"
        anotherhost.data._su_user = "this-should-be-overridden"

        anotherhost.current_op_global_kwargs = {
            "su_user": "override-su-user",
        }

        connect_all(state)

        with patch("pyinfra.connectors.ssh.run_shell_command") as fake_run_command:
            fake_run_command.return_value = MagicMock(), [("stdout", "some-output")]
            fact_data = get_facts(
                state,
                Command,
                args=("yes",),
                kwargs={"_sudo_user": "override-sudo-user"},
            )

        assert fact_data == {anotherhost: "some-output"}

        defaults = _get_executor_defaults(state, anotherhost)
        defaults["sudo"] = True
        defaults["sudo_user"] = "override-sudo-user"
        defaults["su_user"] = "override-su-user"

        fake_run_command.assert_called_with(
            state,
            anotherhost,
            "yes",
            print_input=False,
            print_output=False,
            return_combined_output=True,
            **defaults,
        )

    def test_get_fact_cached(self):
        inventory = make_inventory(hosts=("anotherhost",))
        state = State(inventory, Config())

        fact_hash = "a-fact-hash"
        cached_fact = {"this is a cached fact"}
        anotherhost = inventory.get_host("anotherhost")
        anotherhost.facts[fact_hash] = cached_fact

        connect_all(state)

        with patch("pyinfra.connectors.ssh.run_shell_command") as fake_run_command:
            fake_run_command.return_value = MagicMock(), [("stdout", "some-output")]
            fact_data = get_facts(
                state,
                Command,
                args=("yes",),
                kwargs={"_sudo": True},
                fact_hash=fact_hash,
            )

        assert fact_data == {anotherhost: cached_fact}
        fake_run_command.assert_not_called()

    def test_get_fact_no_args(self):
        inventory = make_inventory(hosts=("host-1",))
        state = State(inventory, Config())

        connect_all(state)

        host_1 = inventory.get_host("host-1")
        defaults = _get_executor_defaults(state, host_1)

        with patch("pyinfra.connectors.ssh.run_shell_command") as fake_run_command:
            fake_run_command.return_value = MagicMock(), [("stdout", "some-output")]
            fact_data = get_facts(state, Arch)

        assert fact_data == {host_1: "some-output"}
        fake_run_command.assert_called_with(
            state,
            host_1,
            Arch.command,
            print_input=False,
            print_output=False,
            return_combined_output=True,
            **defaults,
        )


class TestHostFactsApi(PatchSSHTestCase):
    def test_get_host_fact(self):
        inventory = make_inventory(hosts=("host-1",))
        state = State(inventory, Config())

        connect_all(state)

        host_1 = inventory.get_host("host-1")
        defaults = _get_executor_defaults(state, host_1)

        with patch("pyinfra.connectors.ssh.run_shell_command") as fake_run_command:
            fake_run_command.return_value = MagicMock(), [("stdout", "some-output")]
            fact_data = host_1.get_fact(Command, command="echo hello world")

        assert fact_data == "some-output"
        fake_run_command.assert_called_with(
            state,
            host_1,
            "echo hello world",
            print_input=False,
            print_output=False,
            return_combined_output=True,
            **defaults,
        )

    def test_get_host_fact_sudo(self):
        inventory = make_inventory(hosts=("host-1",))
        state = State(inventory, Config())

        connect_all(state)

        host_1 = inventory.get_host("host-1")
        defaults = _get_executor_defaults(state, host_1)
        defaults["sudo"] = True

        with patch("pyinfra.connectors.ssh.run_shell_command") as fake_run_command:
            fake_run_command.return_value = MagicMock(), [("stdout", "some-output")]
            fact_data = host_1.get_fact(Command, command="echo hello world", _sudo=True)

        assert fact_data == "some-output"
        fake_run_command.assert_called_with(
            state,
            host_1,
            "echo hello world",
            print_input=False,
            print_output=False,
            return_combined_output=True,
            **defaults,
        )

    def test_get_host_fact_sudo_no_args(self):
        inventory = make_inventory(hosts=("host-1",))
        state = State(inventory, Config())

        connect_all(state)

        host_1 = inventory.get_host("host-1")
        defaults = _get_executor_defaults(state, host_1)
        defaults["sudo"] = True

        with patch("pyinfra.connectors.ssh.run_shell_command") as fake_run_command:
            fake_run_command.return_value = MagicMock(), [("stdout", "some-output")]
            fact_data = host_1.get_fact(Arch, _sudo=True)

        assert fact_data == "some-output"
        fake_run_command.assert_called_with(
            state,
            host_1,
            Arch.command,
            print_input=False,
            print_output=False,
            return_combined_output=True,
            **defaults,
        )
