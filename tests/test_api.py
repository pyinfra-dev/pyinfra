import __builtin__ as builtins
from unittest import TestCase
from socket import gaierror, error as socket_error

from mock import patch, mock_open
from paramiko import SSHException, AuthenticationException

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
from pyinfra.api.operation import add_op
from pyinfra.api.operations import run_ops
from pyinfra.api.ssh import connect_all

from pyinfra.modules import files, server


def make_inventory(**kwargs):
    return Inventory(
        ([
            'somehost',
            'anotherhost',
            AuthenticationException,
            SSHException,
            gaierror,
            socket_error
        ], {}),
        test_group=([
            'somehost'
        ], {
            'group_data': 'hello world'
        }),
        ssh_user='vagrant',
        ssh_password='test'
    )


def make_config():
    return Config(
        FAIL_PERCENT=None,
        TIMEOUT=1
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

    def test_connect(self):
        state = State(make_inventory(), make_config())
        connect_all(state)

    def test_connect_password(self):
        state = State(make_inventory(ssh_password='test'), make_config())
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

    def test_file_op(self):
        state = State(make_inventory(), make_config())
        connect_all(state)

        with patch.object(builtins, 'open', mock_open(read_data='test!')):
            add_op(
                state, files.put,
                'files/file.txt',
                '/home/vagrant/file.txt'
            )

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

    def test_run_ops_nowait(self):
        state = State(make_inventory(), make_config())
        connect_all(state)

        add_op(
            state, server.shell,
            'echo "hello world"'
        )

        run_ops(state, nowait=True)
