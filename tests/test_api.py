from unittest import TestCase

from mock import patch
from paramiko import (
    PasswordRequiredException,
    SSHException,
)

from pyinfra.api import Config, State
from pyinfra.api.connect import connect_all
from pyinfra.api.exceptions import NoGroupError, NoHostError, PyinfraError

from .paramiko_util import (
    FakeRSAKey,
    PatchSSHTestCase,
)
from .util import make_inventory


class TestInventoryApi(TestCase):
    def test_inventory_creation(self):
        inventory = make_inventory()

        # Check length
        self.assertEqual(len(inventory.hosts), 2)

        # Get a host
        host = inventory['somehost']
        self.assertEqual(host.data.ssh_user, 'vagrant')

        # Check our group data
        self.assertEqual(
            inventory.get_group_data('test_group'),
            {'group_data': 'hello world'},
        )

    def test_tuple_host_group_inventory_creation(self):
        inventory = make_inventory(
            hosts=[
                ('somehost', {'some_data': 'hello'}),
            ],
            tuple_group=([
                ('somehost', {'another_data': 'world'}),
            ], {
                'tuple_group_data': 'word',
            }),
        )

        # Check host data
        host = inventory['somehost']
        self.assertEqual(host.data.some_data, 'hello')
        self.assertEqual(host.data.another_data, 'world')

        # Check group data
        self.assertEqual(host.data.tuple_group_data, 'word')

    def test_host_and_group_errors(self):
        inventory = make_inventory()

        with self.assertRaises(NoHostError):
            inventory['i-dont-exist']

        with self.assertRaises(NoGroupError):
            getattr(inventory, 'i-dont-exist')


class TestSSHApi(TestCase):
    def setUp(self):
        self.fake_connect_patch = patch('pyinfra.api.connectors.ssh.SSHClient.connect')
        self.fake_connect_mock = self.fake_connect_patch.start()

        self.fake_get_transport_patch = patch('pyinfra.api.connectors.ssh.SSHClient.get_transport')
        self.fake_get_transport_patch.start()

        self.fake_agentrequesthandler_patch = patch(
            'pyinfra.api.connectors.ssh.AgentRequestHandler',
        )
        self.fake_agentrequesthandler_patch.start()

    def tearDown(self):
        self.fake_connect_patch.stop()
        self.fake_get_transport_patch.stop()
        self.fake_agentrequesthandler_patch.stop()

    def test_connect_all(self):
        inventory = make_inventory()
        state = State(inventory, Config())
        connect_all(state)

        self.assertEqual(len(state.active_hosts), 2)

    def test_connect_all_password(self):
        inventory = make_inventory(ssh_password='test')

        # Get a host
        somehost = inventory.get_host('somehost')
        self.assertEqual(somehost.data.ssh_password, 'test')

        state = State(inventory, Config())
        connect_all(state)

        self.assertEqual(len(state.active_hosts), 2)

    def test_connect_with_ssh_key(self):
        state = State(make_inventory(hosts=(
            ('somehost', {'ssh_key': 'testkey'}),
        )), Config())

        with patch('pyinfra.api.connectors.ssh.path.isfile', lambda *args, **kwargs: True), \
                patch('pyinfra.api.connectors.ssh.RSAKey.from_private_key_file') as fake_key_open:

            fake_key = FakeRSAKey()
            fake_key_open.return_value = fake_key

            state.deploy_dir = '/'

            connect_all(state)

            # Check the key was created properly
            fake_key_open.assert_called_with(filename='testkey')

            # And check the Paramiko SSH call was correct
            self.fake_connect_mock.assert_called_with(
                'somehost',
                allow_agent=False,
                look_for_keys=False,
                pkey=fake_key,
                timeout=10,
                username='vagrant',
            )

    def test_connect_with_ssh_key_password(self):
        state = State(make_inventory(hosts=(
            ('somehost', {'ssh_key': 'testkey', 'ssh_key_password': 'testpass'}),
        )), Config())

        with patch(
            'pyinfra.api.connectors.ssh.path.isfile',
            lambda *args, **kwargs: True,
        ), patch(
            'pyinfra.api.connectors.ssh.RSAKey.from_private_key_file',
        ) as fake_key_open:

            def fake_key_open_fail(*args, **kwargs):
                if 'password' not in kwargs:
                    raise PasswordRequiredException()

            fake_key_open.side_effect = fake_key_open_fail

            fake_key = FakeRSAKey()
            fake_key_open.return_value = fake_key

            state.deploy_dir = '/'

            connect_all(state)

            # Check the key was created properly
            fake_key_open.assert_called_with(filename='testkey', password='testpass')

    def test_connect_with_missing_ssh_key(self):
        state = State(make_inventory(hosts=(
            ('somehost', {'ssh_key': 'testkey'}),
        )), Config())

        with self.assertRaises(IOError) as e:
            connect_all(state)

        # Ensure pyinfra style IOError
        self.assertTrue(e.exception.args[0].startswith('No such private key file:'))


class TestStateApi(PatchSSHTestCase):
    def test_fail_percent(self):
        inventory = make_inventory((
            'somehost',
            ('thinghost', {'ssh_hostname': SSHException}),
            'anotherhost',
        ))
        state = State(inventory, Config(FAIL_PERCENT=1))

        # Ensure we would fail at this point
        with self.assertRaises(PyinfraError) as context:
            connect_all(state)

        self.assertEqual(context.exception.args[0], 'Over 1% of hosts failed (33%)')

        # Ensure the other two did connect
        self.assertEqual(len(state.active_hosts), 2)
