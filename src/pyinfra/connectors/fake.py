"""
A fake execution connector that simulates command execution without touching a
real target. Both fact-gathering and operation execution funnel through
``run_shell_command``, so a single interception point drives both.

Responses are configurable via inventory data (the ``fake_responses`` key), which
maps a command matcher to a canned result. Anything not matched succeeds with
empty output by default.
"""

from __future__ import annotations

import os
import random
import re
from typing import TYPE_CHECKING, Any

import gevent
from typing_extensions import Unpack, override

from pyinfra import logger
from pyinfra.api.output import echo
from pyinfra.connectors.base import BaseConnector, ConnectorData, DataMeta
from pyinfra.connectors.util import CommandOutput, OutputLine

if TYPE_CHECKING:
    from collections.abc import Iterator
    from io import IOBase

    from pyinfra.api.arguments import ConnectorArguments
    from pyinfra.api.command import StringCommand

# Default simulated command duration (seconds), so progress bars behave like a
# real deploy rather than completing instantly. Override via env vars or per-host
# ``fake_delay`` / ``fake_delay_jitter`` inventory data.
DEFAULT_DELAY = float(os.environ.get("PYINFRA_FAKE_DELAY", "0.5"))
DEFAULT_DELAY_JITTER = float(os.environ.get("PYINFRA_FAKE_DELAY_JITTER", "0.4"))


class FakeConnectorData(ConnectorData, total=False):
    fake_responses: dict[str | re.Pattern, Any]
    fake_delay: float
    fake_delay_jitter: float


class FakeConnector(BaseConnector):
    """
    The ``@fake`` connector simulates execution locally without running anything,
    which is handy for demos, screenshots, documentation examples and tests.

    Every command "succeeds" (exit code 0) with empty output by default. Specific
    responses can be scripted via the host ``fake_responses`` data, a mapping of a
    command matcher to a canned response.

    The matcher (mapping key) is either:

    + a ``str`` — matched as a **substring** of the command, or
    + a compiled ``re.Pattern`` (``re.compile(...)``) — matched with
      ``pattern.search(command)``, so regular expressions are supported.

    The response (mapping value) is either:

    + a ``str`` / ``list[str]`` of stdout lines, or
    + a ``dict`` with optional ``stdout`` (``str``/``list``), ``stderr``
      (``str``/``list``) and ``success`` (``bool``) keys.

    Matchers are tried in insertion order; the first match wins.

    Each simulated command/transfer also takes a short, slightly randomised
    amount of time (so progress bars behave like a real deploy rather than
    finishing instantly). Tune this with the ``fake_delay`` /
    ``fake_delay_jitter`` host data, or the ``PYINFRA_FAKE_DELAY`` /
    ``PYINFRA_FAKE_DELAY_JITTER`` environment variables. Set the delay to
    ``0`` for instant execution (e.g. in tests).
    """

    __examples_doc__ = """
    Run any command or operation against one or more fake hosts, with no real
    target:

    .. code:: shell

        # A single fake host
        pyinfra @fake exec -- echo "hello world"

        # Multiple named fake hosts (comma separated)
        pyinfra @fake/web-1,@fake/web-2 server.shell "echo hi"

    Script what specific commands return with the ``fake_responses`` host data in
    an inventory file (``inventory.py``). Each key is a matcher, each value the
    canned response:

    .. code:: python

        import re

        hosts = [
            (
                "@fake/web-1",
                {
                    "fake_responses": {
                        # substring match
                        "command -v git": {"success": False},
                        "git --version": "git version 2.40.0",
                        # regexp match (re.Pattern keys use pattern.search())
                        re.compile(r"^apt-get .*install"): {
                            "success": False,
                            "stderr": "E: locked",
                        },
                    },
                    # instant execution for this host
                    "fake_delay": 0,
                },
            ),
        ]

    A response value is either a ``str`` / ``list[str]`` of stdout lines, or a
    ``dict`` with optional ``stdout``, ``stderr`` and ``success`` keys. Matchers
    are tried in insertion order; the first match wins, and unmatched commands
    succeed with no output.
    """

    handles_execution = True

    data_cls = FakeConnectorData
    data_meta = {
        "fake_responses": DataMeta(
            "Mapping of command matcher (substring str or re.Pattern) to a canned response.",
            default={},
        ),
        "fake_delay": DataMeta(
            "Base duration (seconds) to simulate for each command/transfer.",
            default=DEFAULT_DELAY,
        ),
        "fake_delay_jitter": DataMeta(
            "Extra random duration (seconds, 0..jitter) added to each delay.",
            default=DEFAULT_DELAY_JITTER,
        ),
    }

    #: Commands executed against this connector instance, recorded for tests/debug.
    executed_commands: list[str]

    def __init__(self, state, host) -> None:
        super().__init__(state, host)
        self.executed_commands = []

    @override
    @staticmethod
    def make_names_data(name: str | None = None) -> Iterator[tuple[str, dict, list[str]]]:
        if not name:
            yield "@fake", {}, ["@fake"]
            return

        for sub_name in name.split(","):
            sub_name = sub_name.strip()
            if not sub_name:
                continue
            yield f"@fake/{sub_name}", {}, ["@fake"]

    def _lookup_response(self, command_str: str) -> tuple[bool, CommandOutput]:
        fake_responses = self.data.get("fake_responses") or {}

        for matcher, response in fake_responses.items():
            if isinstance(matcher, re.Pattern):
                if not matcher.search(command_str):
                    continue
            elif matcher not in command_str:
                continue

            success = True
            stdout: list[str] = []
            stderr: list[str] = []

            if isinstance(response, dict):
                success = bool(response.get("success", True))
                stdout = _as_lines(response.get("stdout"))
                stderr = _as_lines(response.get("stderr"))
            else:
                stdout = _as_lines(response)

            lines = [OutputLine("stdout", line) for line in stdout]
            lines += [OutputLine("stderr", line) for line in stderr]
            return success, CommandOutput(lines)

        # Default: succeed with no output.
        return True, CommandOutput([])

    def _sleep(self) -> None:
        """Simulate a realistic, non-instant task duration.

        Uses ``gevent.sleep`` so other host greenlets and the progress bar
        continue to run cooperatively while this "command" is in flight.
        """
        delay = self.data.get("fake_delay")
        if delay is None:
            delay = DEFAULT_DELAY
        jitter = self.data.get("fake_delay_jitter")
        if jitter is None:
            jitter = DEFAULT_DELAY_JITTER

        duration = float(delay) + random.uniform(0, max(0.0, float(jitter)))
        if duration > 0:
            gevent.sleep(duration)

    @override
    def run_shell_command(
        self,
        command: str | StringCommand,
        print_output: bool = False,
        print_input: bool = False,
        **arguments: Unpack[ConnectorArguments],
    ) -> tuple[bool, CommandOutput]:
        if isinstance(command, str):
            command_str = command
        else:
            command_str = command.get_masked_value()
        self.executed_commands.append(command_str)

        logger.debug("[fake] simulating command on %s: %s", self.host.name, command_str)

        if print_input:
            echo(f"{self.host.print_prefix}>>> {command_str}", err=True)

        self._sleep()

        status, output = self._lookup_response(command_str)

        if print_output:
            for line in output.output_lines:
                echo(f"{self.host.print_prefix}{line}", err=True)

        return status, output

    @override
    def put_file(
        self,
        filename_or_io: str | IOBase,
        remote_filename: str,
        remote_temp_filename: str | None = None,
        print_output: bool = False,
        print_input: bool = False,
        **arguments: Unpack[ConnectorArguments],
    ) -> bool:
        logger.debug("[fake] simulating put_file on %s: %s", self.host.name, remote_filename)
        self._sleep()
        return True

    @override
    def get_file(
        self,
        remote_filename: str,
        filename_or_io: str | IOBase,
        remote_temp_filename: str | None = None,
        print_output: bool = False,
        print_input: bool = False,
        **arguments: Unpack[ConnectorArguments],
    ) -> bool:
        logger.debug("[fake] simulating get_file on %s: %s", self.host.name, remote_filename)
        self._sleep()
        return True


def _as_lines(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return value.splitlines()
    if isinstance(value, (list, tuple)):
        return [str(line) for line in value]
    return [str(value)]
