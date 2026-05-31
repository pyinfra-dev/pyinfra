from base64 import b64decode
from unittest import TestCase
from unittest.mock import mock_open, patch

import pytest
from paramiko import PKey, ProxyCommand, SSHException

from pyinfra.connectors.sshuserclient import SSHClient
from pyinfra.connectors.sshuserclient.client import AskPolicy, get_ssh_config

CERT_KEY_TYPE = "ssh-ed25519-cert-v01@openssh.com"

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

SSH_CONFIG_INLINE_COMMENTS = """
Host 127.0.0.1
    IdentityFile /id_rsa   # my main key
    User testuser # the test user
    Port 33 # custom port
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

SSH_CONFIG_PROXYJUMP_CONNECTTIMEOUT = """
Host jump
    HostName jump.example.com
    User jumpuser
    ConnectTimeout 7

Host device
    HostName 10.0.0.170
    ProxyJump jump
    ConnectTimeout 5
    User deviceuser
"""

SSH_CONFIG_CONNECTTIMEOUT = """
Host slowhost
    HostName slow.example.com
    User slowuser
    ConnectTimeout 12
"""

SSH_CONFIG_MULTIPLE_KNOWN_HOSTS = """
Host 192.168.1.3
    UserKnownHostsFile ~/.ssh/known_hosts ~/.ssh/known_hosts.infra ~/.ssh/known_hosts.webservers
"""

SSH_CONFIG_IDENTITY_AGENT = """
Host 10.0.0.1
    User agentuser
    IdentityAgent ~/Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock
"""

SSH_CONFIG_IDENTITY_AGENT_NONE = """
Host 10.0.0.2
    User agentuser
    IdentityAgent none
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

        (
            _,
            config,
            forward_agent,
            missing_host_key_policy,
            host_keys_file,
            keep_alive,
            identity_agent,
        ) = client.parse_config(
            "127.0.0.1",
        )

        assert config.get("port") == 22
        assert identity_agent is None

    @patch(
        "pyinfra.connectors.sshuserclient.client.path.exists",
        lambda path: False,
    )
    @patch("pyinfra.connectors.sshuserclient.SSHClient.connect")
    @patch("pyinfra.connectors.sshuserclient.SSHClient.gateway")
    def test_proxyjump_without_ssh_config(self, fake_gateway, fake_ssh_connect):
        client = SSHClient()
        _, config, *_ = client.parse_config(
            "10.0.0.5",
            {"port": 22},
            proxyjump="bastionuser@bastion.example.com",
        )
        fake_ssh_connect.assert_called_once_with(
            "bastion.example.com",
            _pyinfra_ssh_config_file=None,
            port=22,
            sock=None,
            username="bastionuser",
        )
        fake_gateway.assert_called_once_with("10.0.0.5", 22, "10.0.0.5", 22, timeout=None)
        assert config.get("sock") is fake_gateway.return_value

    @patch("pyinfra.connectors.sshuserclient.SSHClient.gateway")
    def test_empty_proxyjump_is_ignored(self, fake_gateway):
        client = SSHClient()
        _, config, *_ = client.parse_config("10.0.0.5", {"port": 22}, proxyjump="")
        assert "sock" not in config
        fake_gateway.assert_not_called()

    @patch("pyinfra.connectors.sshuserclient.client.path.exists", lambda path: False)
    @patch("pyinfra.connectors.sshuserclient.SSHClient.connect")
    @patch("pyinfra.connectors.sshuserclient.SSHClient.gateway")
    def test_proxyjump_override_multiple_hops(self, fake_gateway, fake_ssh_connect):
        # A spaced multi-hop override builds a hop chain, stripping each hop.
        client = SSHClient()
        _, config, *_ = client.parse_config(
            "10.0.0.5",
            {"port": 22},
            proxyjump="alice@jump1, bob@jump2",
        )
        assert fake_ssh_connect.call_count == 2
        first_hop, second_hop = fake_ssh_connect.call_args_list
        assert first_hop.args[0] == "jump1"
        assert first_hop.kwargs["username"] == "alice"
        assert second_hop.args[0] == "jump2"
        assert second_hop.kwargs["username"] == "bob"
        assert config.get("sock") is fake_gateway.return_value

    @patch("pyinfra.connectors.sshuserclient.client.path.exists", lambda path: False)
    @patch("pyinfra.connectors.sshuserclient.SSHClient.connect")
    @patch("pyinfra.connectors.sshuserclient.SSHClient.gateway")
    def test_proxyjump_override_bracketed_ipv6(self, fake_gateway, fake_ssh_connect):
        # A bracketed IPv6 hop with a port resolves the same way the rsync -J
        # path does, so command execution and rsync agree.
        client = SSHClient()
        client.parse_config(
            "10.0.0.5",
            {"port": 22},
            proxyjump="user@[2001:db8::1]:2222",
        )
        fake_ssh_connect.assert_called_once_with(
            "2001:db8::1",
            _pyinfra_ssh_config_file=None,
            port=2222,
            sock=None,
            username="user",
        )

    @patch("pyinfra.connectors.sshuserclient.client.path.exists", lambda path: False)
    @patch("pyinfra.connectors.sshuserclient.SSHClient.connect")
    @patch("pyinfra.connectors.sshuserclient.SSHClient.gateway")
    def test_proxyjump_override_ignores_empty_hops(self, fake_gateway, fake_ssh_connect):
        # A stray trailing comma must not produce an empty hop (connect(None)).
        client = SSHClient()
        client.parse_config(
            "10.0.0.5",
            {"port": 22},
            proxyjump="user@jump,",
        )
        assert fake_ssh_connect.call_count == 1
        assert fake_ssh_connect.call_args.args[0] == "jump"

    @patch("pyinfra.connectors.sshuserclient.client.path.exists", lambda path: False)
    @patch("pyinfra.connectors.sshuserclient.SSHClient.connect")
    @patch("pyinfra.connectors.sshuserclient.SSHClient.gateway")
    def test_proxyjump_hop_inherits_key_search_policy(self, fake_gateway, fake_ssh_connect):
        # The jump leg honours the connection's ssh_look_for_keys / ssh_allow_agent so
        # a ProxyJump doesn't re-scan keys / re-prompt for passphrases. Credentials
        # (pkey/password) are per-host and must NOT be offered to intermediate hops.
        client = SSHClient()
        client.parse_config(
            "10.0.0.5",
            {
                "port": 22,
                "allow_agent": True,
                "look_for_keys": False,
                "pkey": object(),
                "password": "hunter2",
            },
            proxyjump="root@bastion",
        )
        _, hop_kwargs = fake_ssh_connect.call_args
        assert hop_kwargs["look_for_keys"] is False
        assert hop_kwargs["allow_agent"] is True
        # The target's credentials must not leak onto the jump leg.
        assert "pkey" not in hop_kwargs
        assert "password" not in hop_kwargs


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

        (
            _,
            config,
            forward_agent,
            missing_host_key_policy,
            host_keys_file,
            keep_alive,
            identity_agent,
        ) = client.parse_config(
            "127.0.0.1",
        )

        assert config.get("key_filename") == ["/id_rsa", "/id_rsa2"]
        assert config.get("username") == "testuser"
        assert config.get("port") == 33
        assert isinstance(config.get("sock"), ProxyCommand)
        assert forward_agent is False
        assert isinstance(missing_host_key_policy, AskPolicy)
        assert host_keys_file == ("~/.ssh/known_hosts",)  # OpenSSH default
        assert identity_agent is None

        (
            _,
            other_config,
            forward_agent,
            missing_host_key_policy,
            host_keys_file,
            keep_alive,
            identity_agent,
        ) = client.parse_config("192.168.1.1")

        assert other_config.get("username") == "otheruser"
        assert forward_agent is True
        assert isinstance(missing_host_key_policy, AskPolicy)
        assert host_keys_file == ("~/.ssh/test3",)

    @patch(
        "pyinfra.connectors.sshuserclient.client.open",
        mock_open(read_data=SSH_CONFIG_INLINE_COMMENTS),
        create=True,
    )
    def test_load_ssh_config_inline_comments(self):
        """Test that inline comments are stripped from SSH config values (issue #1568)."""
        client = SSHClient()

        (
            _,
            config,
            forward_agent,
            missing_host_key_policy,
            host_keys_file,
            keep_alive,
            identity_agent,
        ) = client.parse_config("127.0.0.1")

        assert config.get("key_filename") == ["/id_rsa"]
        assert config.get("username") == "testuser"
        assert config.get("port") == 33

    @patch(
        "pyinfra.connectors.sshuserclient.client.open",
        mock_open(read_data=SSH_CONFIG_DATA),
        create=True,
    )
    @patch(
        "pyinfra.connectors.sshuserclient.config.open",
        mock_open(read_data=SSH_CONFIG_MULTIPLE_KNOWN_HOSTS),
        create=True,
    )
    def test_load_ssh_config_multiple_known_hosts(self):
        """Test that multiple UserKnownHostsFile entries are parsed correctly (issue #1095)."""
        client = SSHClient()

        (
            _,
            config,
            forward_agent,
            missing_host_key_policy,
            host_keys_files,
            keep_alive,
            identity_agent,
        ) = client.parse_config("192.168.1.3")

        # Verify multiple known hosts files are parsed as a tuple
        assert host_keys_files == (
            "~/.ssh/known_hosts",
            "~/.ssh/known_hosts.infra",
            "~/.ssh/known_hosts.webservers",
        )

    @patch(
        "pyinfra.connectors.sshuserclient.client.open",
        mock_open(read_data=SSH_CONFIG_IDENTITY_AGENT),
        create=True,
    )
    def test_load_ssh_config_identity_agent(self):
        """Test that IdentityAgent is parsed from SSH config."""
        client = SSHClient()

        _, config, _, _, _, _, identity_agent = client.parse_config("10.0.0.1")

        assert config.get("username") == "agentuser"
        assert identity_agent == "~/Library/Group Containers/2BUA8C4S2C.com.1password/t/agent.sock"

    @patch(
        "pyinfra.connectors.sshuserclient.client.open",
        mock_open(read_data=SSH_CONFIG_IDENTITY_AGENT_NONE),
        create=True,
    )
    def test_load_ssh_config_identity_agent_none(self):
        """Test that IdentityAgent set to 'none' is ignored."""
        client = SSHClient()

        _, config, _, _, _, _, identity_agent = client.parse_config("10.0.0.2")

        assert config.get("username") == "agentuser"
        assert identity_agent is None

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
        _, config, forward_agent, _, _, _, _ = client.parse_config(
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
        fake_gateway.assert_called_once_with("192.168.1.2", 1022, "192.168.1.2", 1022, timeout=None)

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
    def test_proxyjump_override_beats_config_proxyjump(self, fake_gateway, fake_ssh_connect):
        client = SSHClient()
        _, config, *_ = client.parse_config(
            "192.168.1.2",
            {"port": 1022},
            ssh_config_file="other_file",
            proxyjump="overrideuser@10.0.0.99",
        )
        # The hop is the override target, not the ssh_config ProxyJump host.
        fake_ssh_connect.assert_called_once_with(
            "10.0.0.99",
            _pyinfra_ssh_config_file="other_file",
            port=22,
            sock=None,
            username="overrideuser",
        )
        assert config.get("sock") is fake_gateway.return_value

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
    @patch("pyinfra.connectors.sshuserclient.SSHClient.connect")
    @patch("pyinfra.connectors.sshuserclient.SSHClient.gateway")
    def test_proxyjump_override_beats_config_proxycommand(self, fake_gateway, fake_ssh_connect):
        client = SSHClient()
        _, config, *_ = client.parse_config(
            "127.0.0.1",
            proxyjump="overrideuser@10.0.0.99",
        )
        # ssh_config ProxyCommand is ignored; a ProxyJump channel is built instead.
        assert not isinstance(config.get("sock"), ProxyCommand)
        assert config.get("sock") is fake_gateway.return_value
        fake_ssh_connect.assert_called_once()
        hop_args, hop_kwargs = fake_ssh_connect.call_args
        assert hop_args[0] == "10.0.0.99"
        assert hop_kwargs["username"] == "overrideuser"

    @patch(
        "pyinfra.connectors.sshuserclient.client.open",
        mock_open(read_data=SSH_CONFIG_CONNECTTIMEOUT),
        create=True,
    )
    def test_connecttimeout_sets_timeout_kwarg(self):
        """Regression test for #971: ``ConnectTimeout`` in ssh_config must be
        propagated so paramiko doesn't hang on its own default."""
        client = SSHClient()
        _, config, *_ = client.parse_config("slowhost")
        assert config.get("timeout") == 12

    @patch(
        "pyinfra.connectors.sshuserclient.client.open",
        mock_open(read_data=SSH_CONFIG_PROXYJUMP_CONNECTTIMEOUT),
        create=True,
    )
    @patch(
        "pyinfra.connectors.sshuserclient.config.open",
        mock_open(read_data=SSH_CONFIG_PROXYJUMP_CONNECTTIMEOUT),
        create=True,
    )
    @patch("pyinfra.connectors.sshuserclient.SSHClient.connect")
    @patch("pyinfra.connectors.sshuserclient.SSHClient.gateway")
    def test_proxyjump_propagates_connecttimeout(self, fake_gateway, fake_ssh_connect):
        """Regression test for #971: ``ConnectTimeout`` on both the target and
        the hop must be honored so neither the hop connect nor the direct-tcpip
        channel can hang forever."""
        client = SSHClient()

        _, config, *_ = client.parse_config("device")

        # Target's ConnectTimeout wins for the channel open.
        assert config.get("timeout") == 5
        # Hop connect receives the hop's own ConnectTimeout (7s, per its own
        # ssh_config block) rather than inheriting the target's 5s.
        fake_ssh_connect.assert_called_once()
        _, kwargs = fake_ssh_connect.call_args
        assert kwargs["timeout"] == 7
        # Channel open (gateway) uses the target's ConnectTimeout.
        fake_gateway.assert_called_once()
        _, gw_kwargs = fake_gateway.call_args
        assert gw_kwargs["timeout"] == 5

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

    @patch("pyinfra.connectors.sshuserclient.client.open", mock_open(), create=True)
    @patch("pyinfra.connectors.sshuserclient.client.ParamikoClient.connect")
    def test_connect_threads_proxyjump_into_parse_config(self, fake_paramiko_connect):
        client = SSHClient()
        stub = ("hostname", {"port": 22}, False, AskPolicy(), (), 0, None)
        with patch.object(SSHClient, "parse_config", return_value=stub) as fake_parse_config:
            client.connect("hostname", _pyinfra_ssh_proxyjump="user@jump")
        assert fake_parse_config.call_args.kwargs["proxyjump"] == "user@jump"

    def test_missing_hostkey(self):
        client = SSHClient()
        # Must be set to something for key saving
        client._host_keys_filename = ""
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


@pytest.fixture
def _clear_ssh_config_cache():
    get_ssh_config.cache = {}
    yield
    get_ssh_config.cache = {}


def _write_ssh_config(config_path, host, **directives):
    body = [f"Host {host}"]
    for key, value in directives.items():
        body.append(f"    {key} {value}")
    config_path.write_text("\n".join(body) + "\n")


def test_parse_config_loads_cert_for_identityfile(
    ssh_ca_keypair, tmp_path, _clear_ssh_config_cache
):
    # ssh_config IdentityFile points at a key with an adjacent -cert.pub; the
    # cert must be attached and key_filename must be dropped so paramiko uses
    # the pkey we built.
    config_path = tmp_path / "ssh_config"
    _write_ssh_config(
        config_path,
        host="myhost",
        IdentityFile=str(ssh_ca_keypair["user_key"]),
    )

    client = SSHClient()
    _, cfg, *_ = client.parse_config("myhost", ssh_config_file=str(config_path))

    assert "key_filename" not in cfg
    assert isinstance(cfg["pkey"], PKey)
    assert cfg["pkey"].public_blob is not None
    assert cfg["pkey"].public_blob.key_type == CERT_KEY_TYPE


def test_parse_config_honours_certificatefile_directive(
    ssh_ca_keypair, tmp_path, _clear_ssh_config_cache
):
    # CertificateFile in ssh_config overrides the implicit <key>-cert.pub
    # lookup. We copy the real cert to a different path and reference it.
    other_cert = tmp_path / "other-cert.pub"
    other_cert.write_bytes(ssh_ca_keypair["user_cert"].read_bytes())

    # Use a bare copy of the key so the implicit lookup would NOT find a cert.
    bare_key = tmp_path / "bare_ed25519"
    bare_key.write_bytes(ssh_ca_keypair["user_key"].read_bytes())

    config_path = tmp_path / "ssh_config"
    _write_ssh_config(
        config_path,
        host="myhost",
        IdentityFile=str(bare_key),
        CertificateFile=str(other_cert),
    )

    client = SSHClient()
    _, cfg, *_ = client.parse_config("myhost", ssh_config_file=str(config_path))

    assert "key_filename" not in cfg
    assert cfg["pkey"].public_blob is not None
    assert cfg["pkey"].public_blob.key_type == CERT_KEY_TYPE


def test_parse_config_keeps_key_filename_when_no_real_identityfile(
    tmp_path, _clear_ssh_config_cache
):
    # IdentityFile that doesn't exist on disk must not crash: fall back to the
    # legacy key_filename path and let paramiko handle it.
    config_path = tmp_path / "ssh_config"
    _write_ssh_config(
        config_path,
        host="myhost",
        IdentityFile=str(tmp_path / "does-not-exist"),
    )

    client = SSHClient()
    _, cfg, *_ = client.parse_config("myhost", ssh_config_file=str(config_path))

    assert "pkey" not in cfg
    assert cfg["key_filename"] == [str(tmp_path / "does-not-exist")]
