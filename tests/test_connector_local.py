from subprocess import PIPE
from unittest import TestCase

from mock import patch

from pyinfra.api import Config, State
from pyinfra.api.connect import connect_all
from pyinfra.api.util import make_command

from .util import make_inventory


class TestLocalConnector(TestCase):
    def setUp(self):
        self.fake_popen_patch = patch('pyinfra.api.connectors.local.Popen')
        self.fake_popen_mock = self.fake_popen_patch.start()

    def tearDown(self):
        self.fake_popen_patch.stop()

    def test_connect_all(self):
        inventory = make_inventory(hosts=('@local',))
        state = State(inventory, Config())
        connect_all(state)
        self.assertEqual(len(state.active_hosts), 1)

    def test_connect_host(self):
        inventory = make_inventory(hosts=('@local',))
        state = State(inventory, Config())
        host = inventory.get_host('@local')
        host.connect(state, for_fact=True)
        self.assertEqual(len(state.active_hosts), 0)

    def test_run_shell_command(self):
        inventory = make_inventory(hosts=('@local',))
        state = State(inventory, Config())

        command = 'echo hi'

        host = inventory.get_host('@local')
        host.run_shell_command(state, command, stdin='hello', print_output=True)

        shell_command = make_command(command)
        self.fake_popen_mock.assert_called_with(
            shell_command, shell=True,
            stdout=PIPE, stderr=PIPE, stdin=PIPE,
        )
