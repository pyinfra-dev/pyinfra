import __builtin__ as builtins
from unittest import TestCase
from socket import gaierror, error as socket_error

from mock import patch, mock_open
from paramiko import SSHException, AuthenticationException

# Patch in paramiko fake classes
from pyinfra.api import ssh
from .paramiko_util import (
    FakeSSHClient, FakeSFTPClient, FakeRSAKey,
    FakeAgentRequestHandler
)
ssh.SSHClient = FakeSSHClient
ssh.SFTPClient = FakeSFTPClient
ssh.RSAKey = FakeRSAKey
ssh.AgentRequestHandler = FakeAgentRequestHandler


from pyinfra.api import Inventory, Config, State
from pyinfra.api.ssh import connect_all, connect
from pyinfra.api.operation import add_op
from pyinfra.api.operations import run_ops
from pyinfra.api.exceptions import PyinfraError

from pyinfra.modules import files, server


def make_inventory(hosts=('somehost', 'anotherhost'), **kwargs):
    return Inventory(
        (hosts, {}),
        test_group=([
            'somehost'
        ], {
            'group_data': 'hello world'
        }),
        ssh_user='vagrant',
        ssh_key='test',
        **kwargs
    )


def make_config(FAIL_PERCENT=0, TIMEOUT=1, **kwargs):
    return Config(
        FAIL_PERCENT=FAIL_PERCENT,
        TIMEOUT=TIMEOUT,
        **kwargs
    )


class TestApi(TestCase):
    def test_inventory_creation(self):
        inventory = make_inventory()

        # Get a host
        host = inventory['somehost']
        self.assertEqual(host.ssh_hostname, 'somehost')
        self.assertEqual(host.data.ssh_user, 'vagrant')

        # Check our group data
        self.assertEqual(
            inventory.get_groups_data(['test_group']).dict(),
            {
                'group_data': 'hello world'
            }
        )

    def test_connect_all(self):
        inventory = make_inventory()
        state = State(inventory, make_config())
        connect_all(state)

        self.assertEqual(len(inventory.connected_hosts), 2)

    def test_connect_all_password(self):
        inventory = make_inventory(ssh_password='test')
        state = State(inventory, make_config())
        connect_all(state)

        self.assertEqual(len(inventory.connected_hosts), 2)

    def test_connect_exceptions_fail(self):
        self.assertEqual(connect(AuthenticationException), None)
        self.assertEqual(connect(SSHException), None)
        self.assertEqual(connect(gaierror), None)
        self.assertEqual(connect(socket_error), None)

    def test_fail_percent(self):
        inventory = make_inventory(('somehost', SSHException))
        state = State(inventory, make_config())

        with self.assertRaises(PyinfraError):
            connect_all(state)

    def test_basic_op(self):
        state = State(make_inventory(), make_config())
        connect_all(state)

        add_op(
            state, files.file,
            '/var/log/pyinfra.log',
            user='pyinfra',
            group='pyinfra',
            mode='644',
            sudo=True
        )

        run_ops(state, print_output=True)

    def test_file_op(self):
        state = State(make_inventory(), make_config())
        connect_all(state)

        # Test normal
        with patch.object(builtins, 'open', mock_open(read_data='test!')):
            add_op(
                state, files.put,
                'files/file.txt',
                '/home/vagrant/file.txt'
            )

        # And with sudo
        with patch.object(builtins, 'open', mock_open(read_data='test!')):
            add_op(
                state, files.put,
                'files/file.txt',
                '/home/vagrant/file.txt',
                sudo=True,
                sudo_user='pyinfra'
            )

        run_ops(state)

    def test_run_ops(self):
        state = State(make_inventory(), make_config())
        connect_all(state)

        add_op(
            state, server.shell,
            'echo "hello world"'
        )

        run_ops(state)

    def test_run_ops_serial(self):
        state = State(make_inventory(), make_config())
        connect_all(state)

        add_op(
            state, server.shell,
            'echo "hello world"'
        )

        run_ops(state, serial=True)

    def test_run_ops_no_wait(self):
        state = State(make_inventory(), make_config())
        connect_all(state)

        add_op(
            state, server.shell,
            'echo "hello world"'
        )

        run_ops(state, no_wait=True)
