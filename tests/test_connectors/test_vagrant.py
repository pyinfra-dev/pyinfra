import json

from unittest import TestCase

from mock import mock_open, patch

from pyinfra.api.connectors.vagrant import get_vagrant_options, make_names_data
from pyinfra.api.exceptions import InventoryError

FAKE_VAGRANT_OPTIONS = {
    'groups': {
        'ubuntu16': ['mygroup'],
    },
    'data': {
        'centos7': {
            'somedata': 'somevalue',
        },
    },
}
FAKE_VAGRANT_OPTIONS_DATA = json.dumps(FAKE_VAGRANT_OPTIONS)


def fake_vagrant_shell(command, splitlines=None):
    if command == 'vagrant status --machine-readable':
        return [
            '1574707743,ubuntu16,provider-name,virtualbox',
            '1574707743,ubuntu16,state,running',
            '1574707743,ubuntu18,state,not_created',
            '1574707743,centos7,state,running',
            '1574707743,centos6,state,running',
        ]
    elif command == 'vagrant ssh-config ubuntu16':
        return [
            'ExtraKey logme!',
            'Host ubuntu16',
            'HostName 127.0.0.1',
            'User vagrant',
            'Port 2222',
            'PasswordAuthentication no',
            'IdentityFile path/to/key',
            '',
        ]
    elif command == 'vagrant ssh-config centos7':
        return [
            '',
            'Host centos7',
            'HostName 127.0.0.1',
            'User vagrant',
            'Port 2200',
            'PasswordAuthentication no',
            'IdentityFile path/to/key',
        ]
    elif command == 'vagrant ssh-config centos6':
        return [
            'Host centos6',
            'HostName 127.0.0.1',
        ]

    return []


@patch('pyinfra.api.connectors.vagrant.local.shell', fake_vagrant_shell)
class TestVagrantConnector(TestCase):
    def tearDown(self):
        get_vagrant_options.cache = {}

    @patch(
        'pyinfra.api.connectors.vagrant.open',
        mock_open(read_data=FAKE_VAGRANT_OPTIONS_DATA),
        create=True,
    )
    @patch('pyinfra.api.connectors.vagrant.path.exists', lambda path: True)
    def test_make_names_data_with_options(self):
        data = make_names_data()

        assert data == [
            (
                '@vagrant/ubuntu16',
                {
                    'ssh_port': '2222',
                    'ssh_user': 'vagrant',
                    'ssh_hostname': '127.0.0.1',
                    'ssh_key': 'path/to/key',
                },
                ['mygroup', '@vagrant'],
            ), (
                '@vagrant/centos7',
                {
                    'ssh_port': '2200',
                    'ssh_user': 'vagrant',
                    'ssh_hostname': '127.0.0.1',
                    'ssh_key': 'path/to/key',
                    'somedata': 'somevalue',
                },
                ['@vagrant'],
            ), (
                '@vagrant/centos6',
                {
                    'ssh_hostname': '127.0.0.1',
                },
                ['@vagrant'],
            ),
        ]

    def test_make_names_data_with_limit(self):
        data = make_names_data(limit=('ubuntu16',))

        assert data == [
            (
                '@vagrant/ubuntu16',
                {
                    'ssh_port': '2222',
                    'ssh_user': 'vagrant',
                    'ssh_hostname': '127.0.0.1',
                    'ssh_key': 'path/to/key',
                },
                ['@vagrant'],
            ),
        ]

    def test_make_names_data_no_matches(self):
        with self.assertRaises(InventoryError):
            make_names_data(limit='nope')
