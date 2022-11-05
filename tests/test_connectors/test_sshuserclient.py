from unittest import TestCase
from unittest.mock import mock_open, patch

from paramiko import ProxyCommand

from pyinfra.connectors.sshuserclient import SSHClient
from pyinfra.connectors.sshuserclient.client import AskPolicy, get_ssh_config

SSH_CONFIG_DATA = """
# Comment
Host 127.0.0.1
    IdentityFile /id_rsa
    IdentityFile /id_rsa2
    User testuser
    Port 33
    ProxyCommand echo thing

Include other_file
"""

SSH_CONFIG_OTHER_FILE = """
Host 192.168.1.1
    User "otheruser"
    ProxyCommand None
    ForwardAgent yes
    UserKnownHostsFile ~/.ssh/test3
"""

SSH_CONFIG_OTHER_FILE_PROXYJUMP = """
Host 192.168.1.2
    User "otheruser"
    ProxyJump nottestuser@127.0.0.1
    ForwardAgent yes
"""

BAD_SSH_CONFIG_DATA = """
&
"""

LOOPING_SSH_CONFIG_DATA = """
Include other_file
"""


class TestSSHUserConfigMissing(TestCase):
    def setUp(self):
        get_ssh_config.cache = {}

    @patch(
        "pyinfra.connectors.sshuserclient.client.path.exists",
        lambda path: False,
    )
    def test_load_ssh_config_no_exist(self):
        client = SSHClient()

        _, config, forward_agent, missing_host_key_policy, host_keys_file = client.parse_config(
            "127.0.0.1",
        )

        assert config.get("port") == 22


@patch(
    "pyinfra.connectors.sshuserclient.client.path.exists",
    lambda path: True,
)
@patch(
    "pyinfra.connectors.sshuserclient.config.glob.iglob",
    lambda path: ["other_file"],
)
@patch(
    "pyinfra.connectors.sshuserclient.config.path.isfile",
    lambda path: True,
)
@patch(
    "pyinfra.connectors.sshuserclient.config.path.expanduser",
    lambda path: path,
)
@patch(
    "pyinfra.connectors.sshuserclient.config.path.isabs",
    lambda path: True,
)
@patch(
    "paramiko.config.LazyFqdn.__str__",
    lambda self: "",
)
class TestSSHUserConfig(TestCase):
    def setUp(self):
        get_ssh_config.cache = {}

    @patch(
        "pyinfra.connectors.sshuserclient.client.open",
        mock_open(read_data=SSH_CONFIG_DATA),
        create=True,
    )
    @patch(
        "pyinfra.connectors.sshuserclient.config.open",
        mock_open(read_data=SSH_CONFIG_OTHER_FILE),
        create=True,
    )
    def test_load_ssh_config(self):
        client = SSHClient()

        _, config, forward_agent, missing_host_key_policy, host_keys_file = client.parse_config(
            "127.0.0.1",
        )

        assert config.get("key_filename") == ["/id_rsa", "/id_rsa2"]
        assert config.get("username") == "testuser"
        assert config.get("port") == 33
        assert isinstance(config.get("sock"), ProxyCommand)
        assert forward_agent is False
        assert isinstance(missing_host_key_policy, AskPolicy)
        assert host_keys_file == "~/.ssh/known_hosts"  # OpenSSH default

        (
            _,
            other_config,
            forward_agent,
            missing_host_key_policy,
            host_keys_file,
        ) = client.parse_config("192.168.1.1")

        assert other_config.get("username") == "otheruser"
        assert forward_agent is True
        assert isinstance(missing_host_key_policy, AskPolicy)
        assert host_keys_file == "~/.ssh/test3"

    @patch(
        "pyinfra.connectors.sshuserclient.client.open",
        mock_open(read_data=BAD_SSH_CONFIG_DATA),
        create=True,
    )
    def test_invalid_ssh_config(self):
        client = SSHClient()

        with self.assertRaises(Exception) as context:
            client.parse_config("127.0.0.1")

        assert context.exception.args[0] == "Unparsable line &"

    @patch(
        "pyinfra.connectors.sshuserclient.client.open",
        mock_open(read_data=LOOPING_SSH_CONFIG_DATA),
        create=True,
    )
    @patch(
        "pyinfra.connectors.sshuserclient.config.open",
        mock_open(read_data=LOOPING_SSH_CONFIG_DATA),
        create=True,
    )
    def test_include_loop_ssh_config(self):
        client = SSHClient()

        with self.assertRaises(Exception) as context:
            client.parse_config("127.0.0.1")

        assert context.exception.args[0] == "Include loop detected in ssh config file: other_file"

    @patch(
        "pyinfra.connectors.sshuserclient.client.open",
        mock_open(read_data=SSH_CONFIG_DATA),
        create=True,
    )
    @patch(
        "pyinfra.connectors.sshuserclient.config.open",
        mock_open(read_data=SSH_CONFIG_OTHER_FILE_PROXYJUMP),
        create=True,
    )
    @patch("pyinfra.connectors.sshuserclient.SSHClient.connect")
    @patch("pyinfra.connectors.sshuserclient.SSHClient.gateway")
    def test_load_ssh_config_proxyjump(self, fake_gateway, fake_ssh_connect):
        client = SSHClient()

        # Load the SSH config with ProxyJump configured
        _, config, forward_agent, _, _ = client.parse_config(
            "192.168.1.2",
            {"port": 1022},
            ssh_config_file="other_file",
        )

        fake_ssh_connect.assert_called_once_with(
            "127.0.0.1",
            _pyinfra_ssh_config_file="other_file",
            port="33",
            sock=None,
            username="nottestuser",
        )
        fake_gateway.assert_called_once_with("192.168.1.2", 1022, "192.168.1.2", 1022)

    @patch("pyinfra.connectors.sshuserclient.client.open", mock_open(), create=True)
    @patch("pyinfra.connectors.sshuserclient.client.ParamikoClient.connect")
    def test_test_paramiko_connect_kwargs(self, fake_paramiko_connect):
        client = SSHClient()
        client.connect("hostname", _pyinfra_ssh_paramiko_connect_kwargs={"test": "kwarg"})

        fake_paramiko_connect.assert_called_once_with(
            "hostname",
            port=22,
            test="kwarg",
        )
