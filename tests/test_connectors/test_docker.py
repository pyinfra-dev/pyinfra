from subprocess import PIPE
from unittest import TestCase

from mock import patch
from six.moves import shlex_quote

from pyinfra.api import Config, State
from pyinfra.api.connect import connect_all
from pyinfra.api.util import make_command

from ..util import make_inventory


def fake_docker_shell(command, splitlines=None):
    if command == 'docker run -d not-an-image sleep 10000':
        return ['containerid']


@patch('pyinfra.api.connectors.vagrant.local.shell', fake_docker_shell)
class TestDockerConnector(TestCase):
    def setUp(self):
        self.fake_popen_patch = patch('pyinfra.api.connectors.local.Popen')
        self.fake_popen_mock = self.fake_popen_patch.start()

    def tearDown(self):
        self.fake_popen_patch.stop()

    def test_connect_all(self):
        inventory = make_inventory(hosts=('@docker/not-an-image',))
        state = State(inventory, Config())
        connect_all(state)
        self.assertEqual(len(state.active_hosts), 1)

    def test_connect_host(self):
        inventory = make_inventory(hosts=('@docker/not-an-image',))
        state = State(inventory, Config())
        host = inventory.get_host('not-an-image')
        host.connect(state, for_fact=True)
        self.assertEqual(len(state.active_hosts), 0)

    def test_run_shell_command(self):
        inventory = make_inventory(hosts=('@docker/not-an-image',))
        state = State(inventory, Config())

        command = 'echo hi'

        host = inventory.get_host('not-an-image')
        host.connect(state)
        host.run_shell_command(state, command, stdin='hello', print_output=True)

        command = shlex_quote(command)
        docker_command = 'docker exec -i containerid sh -c {0}'.format(command)
        shell_command = make_command(docker_command)

        self.fake_popen_mock.assert_called_with(
            shell_command, shell=True,
            stdout=PIPE, stderr=PIPE, stdin=PIPE,
        )
