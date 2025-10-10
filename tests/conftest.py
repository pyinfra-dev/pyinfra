from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Dict
import shlex

import asyncssh
import pytest


class _FakeHostKey:
    def export_public_key(self) -> str:
        return "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFakeHostKeyForTestingOnly"


class _FakeSFTPHandle:
    def __init__(self, storage: Dict[str, bytes], filename: str, mode: str) -> None:
        self._storage = storage
        self._filename = filename
        self._mode = mode

    async def __aenter__(self) -> "_FakeSFTPHandle":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:  # noqa: ANN001
        return False

    async def write(self, data: bytes | str) -> None:
        if "r" in self._mode:
            raise IOError("Cannot write using read handle")
        if isinstance(data, str):
            data = data.encode()
        self._storage[self._filename] = data

    async def read(self) -> bytes:
        if "r" not in self._mode:
            raise IOError("Cannot read using write handle")
        return self._storage.get(self._filename, b"")


class _FakeSFTPClient:
    def __init__(self) -> None:
        self._storage: Dict[str, bytes] = {}

    def exit(self) -> None:  # pragma: no cover - provided for interface compatibility
        pass

    def open(self, filename: str, mode: str):  # noqa: ANN001 - matches asyncssh signature
        return _FakeSFTPHandle(self._storage, filename, mode)


@dataclass
class FakeSSHClient:
    hostname: str
    command_results: Dict[str, Dict[str, Any]]

    def __post_init__(self) -> None:
        self.commands_run: list[str] = []
        self._sftp_client = _FakeSFTPClient()
        self._closed = False

    async def run(
        self,
        command: str,
        *,
        check: bool = False,
        term_type: str | None = None,
        input: str | None = None,
        timeout: int | None = None,
    ) -> SimpleNamespace:
        self.commands_run.append(command)
        result = self.command_results.get(command)
        if result is None:
            try:
                parts = shlex.split(command)
            except ValueError:
                parts = []

            if len(parts) >= 3 and parts[0] in {"sh", "bash"} and parts[1] in {"-c", "-lc"}:
                inner_command = parts[2]
                result = self.command_results.get(inner_command)
        if result is None:
            result = {"stdout": "", "stderr": "", "exit_status": 0}
        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")
        exit_status = result.get("exit_status", 0)
        return SimpleNamespace(stdout=stdout, stderr=stderr, exit_status=exit_status)

    async def start_sftp_client(self) -> _FakeSFTPClient:
        return self._sftp_client

    def get_server_host_key(self) -> _FakeHostKey:
        return _FakeHostKey()

    def close(self) -> None:
        self._closed = True

    async def wait_closed(self) -> None:
        pass


@pytest.fixture
def fake_asyncssh(monkeypatch):
    monkeypatch.setenv("PYINFRA_SSH_CONNECTOR", "async-ssh")

    connections: Dict[str, FakeSSHClient] = {}

    async def _connect(hostname: str, **kwargs):  # noqa: ANN001 - match asyncssh
        client = FakeSSHClient(hostname=hostname, command_results={})
        connections[hostname] = client
        return client

    class _FakeSSHConfig:
        def __init__(self, entries: Dict[str, Dict[str, Any]] | None = None) -> None:
            self._entries = entries or {}

        def lookup(self, hostname: str) -> Dict[str, Any]:
            return self._entries.get(hostname, {})

    def _read_ssh_config(*_args, **_kwargs) -> _FakeSSHConfig:
        return _FakeSSHConfig()

    monkeypatch.setattr(asyncssh, "connect", _connect)
    monkeypatch.setattr(asyncssh, "read_ssh_config", _read_ssh_config, raising=False)
    return connections
