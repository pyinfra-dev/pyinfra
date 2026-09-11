"""
Fake for ``asyncio.create_subprocess_shell`` so connector tests can assert on
the shell commands pyinfra would run locally, without running them.
"""

from __future__ import annotations

from unittest import mock

from .fake_ssh import FakeReader, FakeWriter


class FakeLocalProcess:
    def __init__(self, command, returncode=0, stdout=(), stderr=()):
        self.command = command
        self.returncode = returncode
        self.stdin = FakeWriter()
        self.stdout = FakeReader(stdout, eof_chunk=False)
        self.stderr = FakeReader(stderr, eof_chunk=False)
        self.killed = False

    async def wait(self):
        return self.returncode

    def kill(self):
        self.killed = True


class FakeSubprocess:
    """
    Patch ``pyinfra.connectors.util.asyncio.create_subprocess_shell`` with ``.mock``;
    every created process uses the currently configured ``returncode`` and output.
    """

    def __init__(self):
        self.returncode = 0
        self.stdout: list[str] = []
        self.stderr: list[str] = []
        self.processes: list[FakeLocalProcess] = []
        self.mock = mock.AsyncMock(side_effect=self.create)

    async def create(self, command, **kwargs):
        process = FakeLocalProcess(command, self.returncode, self.stdout, self.stderr)
        self.processes.append(process)
        return process

    @property
    def process(self) -> FakeLocalProcess:
        return self.processes[-1]
