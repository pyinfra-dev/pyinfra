from base64 import b64decode
from unittest import TestCase
from unittest.mock import mock_open, patch

from paramiko import PKey, ProxyCommand, SSHException

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
    # ProxyCommand None # Commented to get test passing with Paramiko > 3
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

# To ensure that we don't remove things from users hostfiles
# we should test that all modifications only append to the
# hostfile, and don't delete any data or comments.
EXAMPLE_KEY_1 = (
    "AAAAB3NzaC1yc2EAAAADAQABAAABgQCj7ndNxQowgcQnjshcLrqPEiiphnt+"
    "VTTvDP6mHBL9j1aNUkY4Ue1gvwnGLVlOhGeYrnZaMgRK6+PKCUXaDbC7qtbW8gIkhL7aGCsOr/"
    "C56SJMy/BCZfxd1nWzAOxSDPgVsmerOBYfNqltV9/hWCqBywINIR+5dIg6JTJ72pcEpEjcYgXk"
    "E2YEFXV1JHnsKgbLWNlhScqb2UmyRkQyytRLtL+38TGxkxCflmO+5Z8CSSNY7GidjMIZ7Q4zMj"
    "A2n1nGrlTDkzwDCsw+wqFPGQA179cnfGWOWRVruj16z6XyvxvjJwbz0wQZ75XK5tKSb7FNyeIE"
    "s4TT4jk+S4dhPeAUC5y+bDYirYgM4GC7uEnztnZyaVWQ7B381AK4Qdrwt51ZqExKbQpTUNn+Ej"
    "qoTwvqNj4kqx5QUCI0ThS/YkOxJCXmPUWZbhjpCg56i+2aB6CmK2JGhn57K5mj0MNdBXA4/Wnw"
    "H6XoPWJzK5Nyu2zB3nAZp+S5hpQs+p1vN1/wsjk="
)

KNOWN_HOSTS_EXAMPLE_DATA = f"""
# this is an important comment

# another comment after the newline

@cert-authority example-domain.lan ssh-rsa {EXAMPLE_KEY_1}

192.168.1.222 ssh-rsa {EXAMPLE_KEY_1}
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

        _, config, forward_agent, missing_host_key_policy, host_keys_file, keep_alive = (
            client.parse_config(
                "127.0.0.1",
            )
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

        _, config, forward_agent, missing_host_key_policy, host_keys_file, keep_alive = (
            client.parse_config(
                "127.0.0.1",
            )
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
            keep_alive,
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
        _, config, forward_agent, _, _, _ = client.parse_config(
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

    def test_missing_hostkey(self):
        client = SSHClient()
        policy = AskPolicy()
        example_hostname = "new_host"
        example_keytype = "ecdsa-sha2-nistp256"
        example_key = (
            "AAAAE2VjZHNhLXNoYTItbmlzdHAyNT"
            "YAAAAIbmlzdHAyNTYAAABBBHNp1NM"
            "ZjxPBuuKwIPfkVJqWaH3oUtW137kIW"
            "P4PlCyACt8zVIIimFhIpwRUidcf7jw"
            "VWPAJvfBjEPqewDApnZQ="
        )

        key = PKey.from_type_string(
            example_keytype,
            b64decode(example_key),
        )

        # Check if AskPolicy respects not importing and properly raises SSHException
        with self.subTest("Check user 'no'"):
            with patch("builtins.input", return_value="n"):
                self.assertRaises(
                    SSHException, lambda: policy.missing_host_key(client, example_hostname, key)
                )

        # Check if AskPolicy properly appends to hostfile
        with self.subTest("Check user 'yes'"):
            mock_data = mock_open(read_data=KNOWN_HOSTS_EXAMPLE_DATA)
            # Read mock hostfile
            with patch("pyinfra.connectors.sshuserclient.client.open", mock_data):
                with patch("paramiko.hostkeys.open", mock_data):
                    with patch("builtins.input", return_value="y"):
                        policy.missing_host_key(client, "new_host", key)

            # Assert that we appended correctly to the file
            write_call_args = mock_data.return_value.write.call_args
            # Ensure we only wrote once and then closed the handle.
            assert len(write_call_args) == 2
            # Ensure we wrote the correct content
            correct_output = f"{example_hostname} {example_keytype} {example_key}\n"
            assert write_call_args[0][0] == correct_output
