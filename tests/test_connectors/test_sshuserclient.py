from unittest import TestCase

from mock import mock_open, patch
from paramiko import ProxyCommand

from pyinfra.api.connectors.sshuserclient import SSHClient

SSH_CONFIG_DATA = '''
# Comment
Host 127.0.0.1
    IdentityFile /id_rsa
    IdentityFile /id_rsa2
    User testuser
    Port 33
    ProxyCommand ssh thing

Include other_file
'''

SSH_CONFIG_OTHER_FILE = '''
Host 192.168.1.1
    User "otheruser"
    ProxyCommand None
    ForwardAgent yes
'''

BAD_SSH_CONFIG_DATA = '''
&
'''

LOOPING_SSH_CONFIG_DATA = '''
Include other_file
'''


@patch(
    'pyinfra.api.connectors.sshuserclient.client.path.exists',
    lambda path: True,
)
class TestSSHUserConfig(TestCase):
    @patch(
        'pyinfra.api.connectors.sshuserclient.client.open',
        mock_open(read_data=SSH_CONFIG_DATA),
        create=True,
    )
    @patch(
        'pyinfra.api.connectors.sshuserclient.config.open',
        mock_open(read_data=SSH_CONFIG_OTHER_FILE),
        create=True,
    )
    @patch(
        'pyinfra.api.connectors.sshuserclient.config.glob.iglob',
        lambda path: ['other_file'],
    )
    @patch(
        'pyinfra.api.connectors.sshuserclient.config.path.isfile',
        lambda path: True,
    )
    @patch(
        'pyinfra.api.connectors.sshuserclient.config.path.isabs',
        lambda path: True,
    )
    def test_load_ssh_config(self):
        client = SSHClient()

        _, config, forward_agent = client.parse_config('127.0.0.1')

        assert config.get('key_filename') == ['/id_rsa', '/id_rsa2']
        assert config.get('username') == 'testuser'
        assert config.get('port') == 33
        assert isinstance(config.get('sock'), ProxyCommand)
        assert forward_agent is False

        _, other_config, forward_agent = client.parse_config('192.168.1.1')

        assert other_config.get('username') == 'otheruser'
        assert forward_agent is True

    @patch(
        'pyinfra.api.connectors.sshuserclient.client.open',
        mock_open(read_data=BAD_SSH_CONFIG_DATA),
        create=True,
    )
    def test_invalid_ssh_config(self):
        client = SSHClient()

        with self.assertRaises(Exception) as context:
            client.parse_config('127.0.0.1')

        assert context.exception.args[0] == 'Unparsable line &'

    @patch(
        'pyinfra.api.connectors.sshuserclient.client.open',
        mock_open(read_data=LOOPING_SSH_CONFIG_DATA),
        create=True,
    )
    @patch(
        'pyinfra.api.connectors.sshuserclient.config.open',
        mock_open(read_data=LOOPING_SSH_CONFIG_DATA),
        create=True,
    )
    @patch(
        'pyinfra.api.connectors.sshuserclient.config.glob.iglob',
        lambda path: ['other_file'],
    )
    @patch(
        'pyinfra.api.connectors.sshuserclient.config.path.isfile',
        lambda path: True,
    )
    @patch(
        'pyinfra.api.connectors.sshuserclient.config.path.expanduser',
        lambda path: path,
    )
    def test_include_loop_ssh_config(self):
        client = SSHClient()

        with self.assertRaises(Exception) as context:
            client.parse_config('127.0.0.1')

        assert context.exception.args[0] == 'Include loop detected in ssh config file: other_file'
