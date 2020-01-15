from socket import (
    error as socket_error,
    gaierror,
)
from unittest import TestCase

from mock import patch
from paramiko import (
    AuthenticationException,
    PasswordRequiredException,
    SSHException,
)

from pyinfra.api import Config, State
from pyinfra.api.connect import connect_all
from pyinfra.api.exceptions import PyinfraError

from ..paramiko_util import FakeRSAKey
from ..util import make_inventory


class TestSSHConnector(TestCase):
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

    def test_connect_host(self):
        inventory = make_inventory()
        state = State(inventory, Config())
        host = inventory.get_host('somehost')
        host.connect(state, for_fact=True)
        self.assertEqual(len(state.active_hosts), 0)

    def test_connect_all_password(self):
        inventory = make_inventory(ssh_password='test')

        # Get a host
        somehost = inventory.get_host('somehost')
        self.assertEqual(somehost.data.ssh_password, 'test')

        state = State(inventory, Config())
        connect_all(state)

        self.assertEqual(len(state.active_hosts), 2)

    @patch('pyinfra.api.connectors.ssh.path.isfile', lambda *args, **kwargs: True)
    @patch('pyinfra.api.connectors.ssh.RSAKey.from_private_key_file')
    def test_connect_exceptions(self, fake_key_open):
        for exception_class in (
            AuthenticationException,
            SSHException,
            gaierror,
            socket_error,
            EOFError,
        ):
            state = State(make_inventory(hosts=(
                ('somehost', {'ssh_key': 'testkey'}),
            )), Config())

            def raise_exception(*args, **kwargs):
                raise exception_class

            self.fake_connect_mock.side_effect = raise_exception

            with self.assertRaises(PyinfraError):
                connect_all(state)

            assert len(state.active_hosts) == 0

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

        # Check that loading the same key again is cached in the state
        second_state = State(make_inventory(hosts=(
            ('somehost', {'ssh_key': 'testkey'}),
        )), Config())
        second_state.private_keys = state.private_keys

        connect_all(second_state)

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

    def test_connect_with_ssh_key_missing_password(self):
        state = State(make_inventory(hosts=(
            ('somehost', {'ssh_key': 'testkey'}),
        )), Config())

        with patch(
            'pyinfra.api.connectors.ssh.path.isfile',
            lambda *args, **kwargs: True,
        ), patch(
            'pyinfra.api.connectors.ssh.RSAKey.from_private_key_file',
        ) as fake_key_open:

            def fake_key_open_fail(*args, **kwargs):
                raise PasswordRequiredException

            fake_key_open.side_effect = fake_key_open_fail

            fake_key = FakeRSAKey()
            fake_key_open.return_value = fake_key

            state.deploy_dir = '/'

            with self.assertRaises(PyinfraError) as e:
                connect_all(state)

            assert e.exception.args[0] == (
                'Private key file (testkey) is encrypted, set ssh_key_password '
                'to use this key'
            )

    def test_connect_with_ssh_key_wrong_password(self):
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
                    raise PasswordRequiredException
                raise SSHException

            fake_key_open.side_effect = fake_key_open_fail

            fake_key = FakeRSAKey()
            fake_key_open.return_value = fake_key

            state.deploy_dir = '/'

            with self.assertRaises(PyinfraError) as e:
                connect_all(state)

            assert e.exception.args[0] == 'Incorrect password for private key: testkey'

    def test_connect_with_missing_ssh_key(self):
        state = State(make_inventory(hosts=(
            ('somehost', {'ssh_key': 'testkey'}),
        )), Config())

        with self.assertRaises(IOError) as e:
            connect_all(state)

        # Ensure pyinfra style IOError
        self.assertTrue(e.exception.args[0].startswith('No such private key file:'))
