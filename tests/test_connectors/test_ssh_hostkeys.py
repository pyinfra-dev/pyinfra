from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock

import asyncssh

from pyinfra.api.exceptions import ConnectError
from pyinfra.connectors.ssh_hostkeys import (
    PyinfraSSHClient,
    append_known_host,
    get_host_key_policy,
    resolve_known_hosts_files,
)


def make_public_key():
    return asyncssh.generate_private_key("ssh-ed25519").convert_to_public()


class TestHostKeyPolicy(TestCase):
    def test_get_host_key_policy(self):
        assert get_host_key_policy(None) == "ask"
        assert get_host_key_policy("ask") == "ask"
        assert get_host_key_policy("no") == "off"
        assert get_host_key_policy("off") == "off"
        assert get_host_key_policy("yes") == "yes"
        assert get_host_key_policy("accept-new") == "accept-new"

    def test_get_host_key_policy_invalid(self):
        with self.assertRaises(ConnectError):
            get_host_key_policy("maybe")

    def test_resolve_known_hosts_files(self):
        default = str(Path("~/.ssh/known_hosts").expanduser())

        assert resolve_known_hosts_files(None) is None
        assert resolve_known_hosts_files([]) == [default]
        assert resolve_known_hosts_files(()) == [default]
        assert resolve_known_hosts_files(b"") == [default]
        assert resolve_known_hosts_files("~/.ssh/other") == [str(Path("~/.ssh/other").expanduser())]
        assert resolve_known_hosts_files(["/a", "/b"]) == ["/a", "/b"]


class TestPyinfraSSHClient(TestCase):
    def setUp(self):
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.known_hosts = Path(temp_dir.name) / "known_hosts"

    def make_client(self, policy):
        return PyinfraSSHClient(policy, [str(self.known_hosts)])

    def known_host_keys(self, host="somehost", port=22):
        if not self.known_hosts.is_file():
            return []
        return list(asyncssh.match_known_hosts(str(self.known_hosts), host, "1.2.3.4", port)[0])

    def test_append_known_host(self):
        key = make_public_key()
        append_known_host(str(self.known_hosts), "somehost", 22, key)
        append_known_host(str(self.known_hosts), "otherhost", 2222, key)

        lines = self.known_hosts.read_text().splitlines()
        assert len(lines) == 2
        assert lines[0].startswith("somehost ssh-ed25519 ")
        assert lines[1].startswith("[otherhost]:2222 ssh-ed25519 ")
        assert self.known_host_keys("somehost") == [key]
        assert self.known_host_keys("otherhost", 2222) == [key]

    def test_accept_new_saves_key(self):
        key = make_public_key()
        client = self.make_client("accept-new")

        assert client.validate_host_public_key("somehost", "1.2.3.4", 22, key) is True
        assert self.known_host_keys() == [key]

    def test_changed_key_is_rejected(self):
        key = make_public_key()
        append_known_host(str(self.known_hosts), "somehost", 22, key)

        for policy in ("accept-new", "off", "ask", "yes"):
            client = self.make_client(policy)
            with mock.patch("builtins.input", return_value="y"):
                assert (
                    client.validate_host_public_key("somehost", "1.2.3.4", 22, make_public_key())
                    is False
                )

        assert self.known_host_keys() == [key]

    def test_strict_rejects_unknown_key(self):
        client = self.make_client("yes")

        assert (
            client.validate_host_public_key("somehost", "1.2.3.4", 22, make_public_key()) is False
        )
        assert not self.known_hosts.exists()

    def test_off_accepts_without_saving(self):
        client = self.make_client("off")

        assert client.validate_host_public_key("somehost", "1.2.3.4", 22, make_public_key()) is True
        assert not self.known_hosts.exists()

    def test_ask_policy(self):
        key = make_public_key()
        client = self.make_client("ask")

        with mock.patch("builtins.input", return_value="n"):
            assert client.validate_host_public_key("somehost", "1.2.3.4", 22, key) is False
        assert not self.known_hosts.exists()

        with mock.patch("builtins.input", return_value="y"):
            assert client.validate_host_public_key("somehost", "1.2.3.4", 22, key) is True
        assert self.known_host_keys() == [key]

    def test_no_known_hosts_file_does_not_save(self):
        client = PyinfraSSHClient("accept-new", [])

        assert client.validate_host_public_key("somehost", "1.2.3.4", 22, make_public_key()) is True
