from __future__ import annotations

import os
from typing import Dict

import asyncssh
import pytest

from pyinfra.api import Config, State, StringCommand
from pyinfra.api.connect import connect_all, disconnect_all

from ..util import make_inventory


@pytest.fixture(autouse=True)
def _force_async_ssh_connector(monkeypatch):
    monkeypatch.setenv("PYINFRA_SSH_CONNECTOR", "async-ssh")


def test_connect_all_activates_hosts(fake_asyncssh):
    inventory = make_inventory()
    state = State(inventory, Config())

    connect_all(state)

    assert {host.name for host in state.active_hosts} == {"somehost", "anotherhost"}
    assert set(fake_asyncssh.keys()) == {"somehost", "anotherhost"}

    disconnect_all(state)


def test_run_shell_command_uses_asyncssh(fake_asyncssh):
    inventory = make_inventory()
    state = State(inventory, Config())

    connect_all(state)
    host = inventory.get_host("somehost")

    connection = fake_asyncssh[host.name]
    connection.command_results["echo hello"] = {"stdout": "hello\n", "stderr": "", "exit_status": 0}

    status, output = host.run_shell_command(StringCommand("echo", "hello"))

    assert status is True
    assert output.stdout_lines == ["hello"]
    assert any("echo hello" in command for command in connection.commands_run)

    disconnect_all(state)


def test_put_file_uses_scp_protocol(fake_asyncssh, monkeypatch, tmp_path):
    inventory = make_inventory(override_data={"ssh_file_transfer_protocol": "scp"})
    state = State(inventory, Config())

    remote_files: Dict[str, Dict[str, bytes]] = {}

    async def _scp_stub(src, dst, **kwargs):  # type: ignore[override]
        # Upload: local path -> (connection, remote_path)
        if isinstance(dst, tuple):
            client, remote_path = dst
            with open(src, "rb") as src_file:
                data = src_file.read()
            remote_files.setdefault(client.hostname, {})[remote_path] = data
            return

        # Download: (connection, remote_path) -> local path
        client, remote_path = src
        data = remote_files.get(client.hostname, {}).get(remote_path)
        if data is None:
            raise FileNotFoundError(remote_path)
        directory = os.path.dirname(dst)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(dst, "wb") as dest_file:
            dest_file.write(data)

    monkeypatch.setattr(asyncssh, "scp", _scp_stub)

    connect_all(state)
    host = inventory.get_host("somehost")

    local_file = tmp_path / "upload.txt"
    local_file.write_text("hello scp")

    assert host.put_file(str(local_file), "/remote/upload.txt") is True
    assert remote_files["somehost"]["/remote/upload.txt"] == b"hello scp"

    disconnect_all(state)


def test_get_file_uses_scp_protocol(fake_asyncssh, monkeypatch, tmp_path):
    inventory = make_inventory(override_data={"ssh_file_transfer_protocol": "scp"})
    state = State(inventory, Config())

    remote_files: Dict[str, Dict[str, bytes]] = {"somehost": {"/remote/file.txt": b"from-remote"}}

    async def _scp_stub(src, dst, **kwargs):  # type: ignore[override]
        if isinstance(dst, tuple):
            client, remote_path = dst
            with open(src, "rb") as src_file:
                data = src_file.read()
            remote_files.setdefault(client.hostname, {})[remote_path] = data
            return

        client, remote_path = src
        data = remote_files.get(client.hostname, {}).get(remote_path)
        if data is None:
            raise FileNotFoundError(remote_path)
        directory = os.path.dirname(dst)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(dst, "wb") as dest_file:
            dest_file.write(data)

    monkeypatch.setattr(asyncssh, "scp", _scp_stub)

    connect_all(state)
    host = inventory.get_host("somehost")

    destination = tmp_path / "download.txt"
    assert host.get_file("/remote/file.txt", str(destination)) is True
    assert destination.read_text() == "from-remote"

    disconnect_all(state)


def test_paramiko_kwargs_compatibility(tmp_path):
    key = asyncssh.generate_private_key("ssh-ed25519")
    key_file = tmp_path / "id_test"
    key_file.write_text(key.export_private_key().decode(), encoding="utf-8")

    inventory = make_inventory(
        override_data={
            "ssh_paramiko_connect_kwargs": {
                "hostname": "overridehost",
                "username": "otheruser",
                "password": "secret",
                "port": 2222,
                "timeout": 12,
                "auth_timeout": 34,
                "allow_agent": False,
                "look_for_keys": False,
                "compress": True,
                "key_filename": str(key_file),
            }
        }
    )

    _state = State(inventory, Config())
    host = inventory.get_host("somehost")
    connector = host.connector

    hostname, kwargs = connector._build_connect_kwargs(host.name, "accept-new")

    assert hostname == "overridehost"
    assert kwargs["username"] == "otheruser"
    assert kwargs["password"] == "secret"
    assert kwargs["port"] == 2222
    assert kwargs["connect_timeout"] == 12
    assert kwargs["login_timeout"] == 34
    assert kwargs["agent_path"] == ()
    assert kwargs["client_keys"] and len(kwargs["client_keys"]) == 1
    assert kwargs["compression_algs"] == ["zlib@openssh.com", "zlib"]


def test_private_key_certificates_are_loaded(tmp_path):
    key = asyncssh.generate_private_key("ssh-ed25519")
    key_file = tmp_path / "id_ed25519"
    key_file.write_text(key.export_private_key().decode(), encoding="utf-8")

    cert_file = tmp_path / "id_ed25519-cert.pub"
    cert_file.write_text(key.export_public_key().decode(), encoding="utf-8")

    inventory = make_inventory(override_data={"ssh_key": str(key_file)})
    _state = State(inventory, Config())
    host = inventory.get_host("somehost")
    connector = host.connector

    _, kwargs = connector._build_connect_kwargs(host.name, "accept-new")

    assert kwargs.get("client_keys")
    assert kwargs.get("client_certs")
    assert len(kwargs["client_certs"]) == 1


def test_default_ssh_config_is_loaded(fake_asyncssh, tmp_path, monkeypatch):
    home = tmp_path / "home"
    config_dir = home / ".ssh"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "config"
    config_file.write_text("Host somehost\n  User alternative\n", encoding="utf-8")

    monkeypatch.setenv("HOME", str(home))

    calls: list[str] = []

    class _TrackingConfig:
        def lookup(self, hostname: str) -> Dict[str, str]:
            return {}

    def _read_config(path: str, *_args, **_kwargs):
        calls.append(path)
        return _TrackingConfig()

    monkeypatch.setattr(asyncssh, "read_ssh_config", _read_config, raising=False)

    inventory = make_inventory()
    state = State(inventory, Config())

    connect_all(state)

    assert calls
    assert set(calls) == {str(config_file)}

    disconnect_all(state)


def test_accept_new_writes_default_known_hosts(fake_asyncssh, tmp_path, monkeypatch):
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))

    inventory = make_inventory(override_data={"ssh_strict_host_key_checking": "accept-new"})
    state = State(inventory, Config())

    connect_all(state)

    known_hosts_path = home / ".ssh" / "known_hosts"
    assert known_hosts_path.exists()
    contents = known_hosts_path.read_text()
    assert "somehost" in contents

    disconnect_all(state)


def test_accept_new_detects_host_key_mismatch(fake_asyncssh, tmp_path, monkeypatch):
    home = tmp_path / "home"
    known_hosts_dir = home / ".ssh"
    known_hosts_dir.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))

    # Write a different host key to trigger mismatch detection
    other_key = asyncssh.generate_private_key("ssh-ed25519").export_public_key().decode()
    mismatch_line = f"somehost {other_key}\n"
    (known_hosts_dir / "known_hosts").write_text(mismatch_line, encoding="utf-8")

    inventory = make_inventory(override_data={"ssh_strict_host_key_checking": "accept-new"})
    state = State(inventory, Config())

    connect_all(state)

    host = inventory.get_host("somehost")
    assert host not in state.active_hosts
    assert host in state.failed_hosts

    disconnect_all(state)
