"""
Fakes for asyncssh so tests can exercise the SSH connector, and everything built
on top of it, without any network access.
"""

from __future__ import annotations

import asyncio
from inspect import isclass
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, TestCase, mock


class FakeWriter:
    def __init__(self):
        self.written: list[bytes] = []
        self.eof = False

    def write(self, data):
        self.written.append(data)

    async def drain(self):
        pass

    def write_eof(self):
        self.eof = True


class FakeReader:
    """
    Yields lines like an asyncssh ``SSHReader``, including the empty chunk
    asyncssh produces at EOF.
    """

    def __init__(self, lines=(), delay=0, eof_chunk=True):
        self.lines = [line if isinstance(line, bytes) else line.encode() for line in lines]
        self.delay = delay
        self.eof_chunk = eof_chunk

    def __aiter__(self):
        return self._iterate()

    async def _iterate(self):
        if self.delay:
            await asyncio.sleep(self.delay)
        for line in self.lines:
            yield line if line.endswith(b"\n") else line + b"\n"
        if self.eof_chunk:
            yield b""


class FakeProcess:
    def __init__(self, command, term_type=None, exit_status=0, stdout=(), stderr=(), delay=0):
        self.command = command
        self.term_type = term_type
        self.exit_status = exit_status
        self.stdin = FakeWriter()
        self.stdout = FakeReader(stdout, delay=delay)
        self.stderr = FakeReader(stderr, delay=delay)
        self.closed = False

    async def wait(self):
        return self

    def close(self):
        self.closed = True


class FakeSFTPFile:
    def __init__(self, sftp, path, mode):
        self.sftp = sftp
        self.path = path
        self.mode = mode

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def read(self, size=-1):
        return self.sftp.read_data.pop(0) if self.sftp.read_data else b""

    async def write(self, data):
        self.sftp.written.setdefault(self.path, []).append(data)


class FakeSFTPClient:
    def __init__(self):
        self.read_data: list[bytes] = []
        self.written: dict[str, list[bytes]] = {}
        self.opened: list[tuple[str, str]] = []
        self.open_side_effect = None

    def open(self, path, mode):
        self.opened.append((path, mode))
        if self.open_side_effect is not None:
            raise self.open_side_effect
        return FakeSFTPFile(self, path, mode)

    def exit(self):
        pass


class FakeSSHClientConnection:
    """
    Records every command executed and returns scripted responses, defaulting to
    exit status 0 with no output.
    """

    def __init__(self):
        self.commands: list[str] = []
        self.processes: list[FakeProcess] = []
        # Each entry is (exit_status, stdout_lines, stderr_lines, delay), consumed in order.
        self.responses: list[tuple[int, list[str], list[str], float]] = []
        self.sftp = FakeSFTPClient()
        self.sftp_side_effect = None
        self.closed = False

    def add_response(self, exit_status=0, stdout=(), stderr=(), delay=0):
        self.responses.append((exit_status, list(stdout), list(stderr), delay))

    async def create_process(self, command, term_type=None, encoding=None, **kwargs):
        self.commands.append(command)
        if self.responses:
            exit_status, stdout, stderr, delay = self.responses.pop(0)
        else:
            exit_status, stdout, stderr, delay = 0, [], [], 0
        process = FakeProcess(command, term_type, exit_status, stdout, stderr, delay)
        self.processes.append(process)
        return process

    async def start_sftp_client(self):
        if self.sftp_side_effect is not None:
            raise self.sftp_side_effect
        return self.sftp

    def close(self):
        self.closed = True

    async def wait_closed(self):
        pass


class FakeKey:
    def __init__(self, filename, passphrase=None):
        self.filename = filename
        self.passphrase = passphrase


class FakeCertificate:
    def __init__(self, filename):
        self.filename = filename


class FakeAsyncSSH:
    """
    Stand-in for the parts of asyncssh the SSH connector touches.
    """

    def __init__(self):
        self.connect_calls: list[dict] = []
        self.connections: list[FakeSSHClientConnection] = []
        # An exception (instance or class) or a list of them / None, raised per connect call.
        self.connect_side_effect = None
        self.connect_mock = mock.AsyncMock(side_effect=self.connect)

    async def connect(self, **kwargs):
        self.connect_calls.append(kwargs)

        host = kwargs.get("host")
        if isclass(host) and issubclass(host, BaseException):
            raise host()

        side_effect = self.connect_side_effect
        if isinstance(side_effect, list):
            side_effect = side_effect.pop(0) if side_effect else None
        if side_effect is not None:
            raise side_effect() if isclass(side_effect) else side_effect

        connection = FakeSSHClientConnection()
        self.connections.append(connection)
        return connection

    @property
    def connection(self) -> FakeSSHClientConnection:
        return self.connections[-1]

    @staticmethod
    def make_options(**kwargs):
        return SimpleNamespace(
            host=kwargs.get("host"),
            known_hosts=kwargs.get("known_hosts", []),
        )

    @staticmethod
    def read_private_key(filename, passphrase=None):
        return FakeKey(filename, passphrase)

    @staticmethod
    def read_certificate(filename):
        return FakeCertificate(filename)


class PatchSSHTestCase(TestCase):
    """
    Patches asyncssh such that SSH connections and commands succeed without any
    network access. ``self.fake_ssh`` records connections and executed commands.
    """

    fake_ssh: FakeAsyncSSH

    def setUp(self):
        super().setUp()
        self.fake_ssh = FakeAsyncSSH()

        for target, replacement in (
            ("pyinfra.connectors.ssh.asyncssh.connect", self.fake_ssh.connect_mock),
            (
                "pyinfra.connectors.ssh.asyncssh.SSHClientConnectionOptions",
                self.fake_ssh.make_options,
            ),
            ("pyinfra.connectors.ssh_util.read_private_key", self.fake_ssh.read_private_key),
            ("pyinfra.connectors.ssh_util.read_certificate", self.fake_ssh.read_certificate),
        ):
            patcher = mock.patch(target, replacement)
            patcher.start()
            self.addCleanup(patcher.stop)


class AsyncPatchSSHTestCase(PatchSSHTestCase, IsolatedAsyncioTestCase):
    """
    As ``PatchSSHTestCase`` but test methods may be coroutines, for the async API.
    """
