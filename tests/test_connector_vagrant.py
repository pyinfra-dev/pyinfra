from unittest import TestCase

from mock import patch

from pyinfra.api.connectors.util import split_combined_output
from pyinfra.api.connectors.vagrant import make_names_data
from pyinfra.api.exceptions import InventoryError


def fake_vagrant_shell(command, splitlines=None):
    if command == 'vagrant status --machine-readable':
        return [
            '1574707743,ubuntu16,provider-name,virtualbox',
            '1574707743,ubuntu16,state,running',
            '1574707743,ubuntu18,state,not_created',
            '1574707743,centos7,state,running',
        ]
    elif command == 'vagrant ssh-config ubuntu16':
        return [
            'ExtraKey logme!',
            '',
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
            'Host centos7',
            'HostName 127.0.0.1',
            'User vagrant',
            'Port 2200',
            'PasswordAuthentication no',
            'IdentityFile path/to/key',
        ]

    return []


@patch('pyinfra.api.connectors.vagrant.local.shell', fake_vagrant_shell)
class TestVagrantConnector(TestCase):
    def test_make_names_data_with_limit(self):
        data = make_names_data(limit=('ubuntu16', 'centos7'))

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
            ), (
                '@vagrant/centos7',
                {
                    'ssh_port': '2200',
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


class TestConnectorUtils(TestCase):
    def test_split_combined_output_works(self):
        results = split_combined_output([
            ('stdout', 'stdout1'),
            ('stdout', 'stdout2'),
            ('stderr', 'stderr1'),
            ('stdout', 'stdout3'),
        ])

        assert results == (['stdout1', 'stdout2', 'stdout3'], ['stderr1'])

    def test_split_combined_output_raises(self):
        with self.assertRaises(ValueError):
            split_combined_output(['nope', ''])
