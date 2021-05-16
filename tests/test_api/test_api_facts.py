from mock import MagicMock, patch

from pyinfra.api import Config, State
from pyinfra.api.connect import connect_all
from pyinfra.api.exceptions import PyinfraError
from pyinfra.api.facts import get_facts

from ..paramiko_util import (
    PatchSSHTestCase,
)
from ..util import make_inventory


class TestOperationsApi(PatchSSHTestCase):
    def test_get_fact(self):
        inventory = make_inventory(hosts=('anotherhost',))
        state = State(inventory, Config())

        anotherhost = inventory.get_host('anotherhost')

        connect_all(state)

        with patch('pyinfra.api.connectors.ssh.run_shell_command') as fake_run_command:
            fake_run_command.return_value = MagicMock(), [('stdout', 'some-output')]
            fact_data = get_facts(state, 'command', ('yes',))

        assert fact_data == {anotherhost: 'some-output'}

        fake_run_command.assert_called_with(
            state,
            anotherhost,
            'yes',
            print_input=False,
            print_output=False,
            shell_executable=None,
            su_user=None,
            sudo=False,
            sudo_user=None,
            timeout=None,
            env={},
            use_sudo_password=False,
            return_combined_output=True,
        )

    def test_get_fact_current_op_meta(self):
        inventory = make_inventory(hosts=('anotherhost',))
        state = State(inventory, Config())

        anotherhost = inventory.get_host('anotherhost')

        connect_all(state)
        state.current_op_global_kwargs = {
            'sudo': True,
            'sudo_user': 'someuser',
            'use_sudo_password': True,
            'su_user': 'someuser',
            'ignore_errors': False,
            'timeout': 10,
            'env': {'HELLO': 'WORLD'},
        }

        with patch('pyinfra.api.connectors.ssh.run_shell_command') as fake_run_command:
            fake_run_command.return_value = MagicMock(), [('stdout', 'some-output')]
            fact_data = get_facts(state, 'command', ('yes',))

        assert fact_data == {anotherhost: 'some-output'}

        fake_run_command.assert_called_with(
            state,
            anotherhost,
            'yes',
            print_input=False,
            print_output=False,
            shell_executable=None,
            su_user='someuser',
            sudo=True,
            sudo_user='someuser',
            timeout=10,
            env={'HELLO': 'WORLD'},
            use_sudo_password=True,
            return_combined_output=True,
        )

    def test_get_fact_error(self):
        inventory = make_inventory(hosts=('anotherhost',))
        state = State(inventory, Config())

        anotherhost = inventory.get_host('anotherhost')

        connect_all(state)

        with patch('pyinfra.api.connectors.ssh.run_shell_command') as fake_run_command:
            fake_run_command.return_value = False, MagicMock()

            with self.assertRaises(PyinfraError) as context:
                get_facts(state, 'command', ('fail command',))

        assert context.exception.args[0] == 'No hosts remaining!'

        fake_run_command.assert_called_with(
            state,
            anotherhost,
            'fail command',
            print_input=False,
            print_output=False,
            shell_executable=None,
            su_user=None,
            sudo=False,
            sudo_user=None,
            timeout=None,
            env={},
            use_sudo_password=False,
            return_combined_output=True,
        )

    def test_get_fact_error_ignore(self):
        inventory = make_inventory(hosts=('anotherhost',))
        state = State(inventory, Config())

        anotherhost = inventory.get_host('anotherhost')

        connect_all(state)
        state.current_op_global_kwargs = {
            'sudo': False,
            'sudo_user': None,
            'use_sudo_password': False,
            'su_user': None,
            'ignore_errors': True,
            'timeout': None,
            'env': {},
        }

        with patch('pyinfra.api.connectors.ssh.run_shell_command') as fake_run_command:
            fake_run_command.return_value = False, MagicMock()
            fact_data = get_facts(state, 'command', ('fail command',))

        assert fact_data == {anotherhost: None}

        fake_run_command.assert_called_with(
            state,
            anotherhost,
            'fail command',
            print_input=False,
            print_output=False,
            shell_executable=None,
            su_user=None,
            sudo=False,
            sudo_user=None,
            timeout=None,
            env={},
            use_sudo_password=False,
            return_combined_output=True,
        )
