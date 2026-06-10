from __future__ import annotations

from typing_extensions import override

from pyinfra.api import FactBase, HiddenValue, QuoteString, StringCommand

RUNNING_STATES = ("RUNNING", "STARTING")
STOPPED_STATES = ("STOPPED", "STOPPING", "EXITED")
BROKEN_STATES = ("BACKOFF", "FATAL", "UNKNOWN")


def _make_supervisorctl_command(
    config_file: str | None = None,
    server_url: str | None = None,
    username: str | None = None,
    password: str | None = None,
) -> StringCommand:
    command_bits: list[str | QuoteString] = ["supervisorctl"]

    if config_file is not None:
        command_bits.extend(("--configuration", QuoteString(config_file)))

    if server_url is not None:
        command_bits.extend(("--serverurl", QuoteString(server_url)))

    if username is not None:
        command_bits.extend(("--username", QuoteString(username)))

    if password is not None:
        command_bits.extend(("--password", QuoteString(HiddenValue(password))))

    return StringCommand(*command_bits)


class SupervisorctlStatus(FactBase[dict[str, "bool | None"]]):
    """
    Returns a dict of supervisor process names to their running state.

    Processes inside a group are keyed by their full ``group:name`` name.

    + config_file: configuration file to pass to ``supervisorctl`` (``-c``)
    + server_url: URL on which supervisord listens (``-s``)
    + username: username to authenticate with (``-u``)
    + password: password to authenticate with (``-p``)

    .. code:: python

        {
            "web": True,             # RUNNING or STARTING
            "workers:worker_0": False,  # STOPPED, STOPPING or EXITED
            "broken": None,          # BACKOFF, FATAL or UNKNOWN
        }
    """

    default = dict

    @override
    def requires_command(self, *args, **kwargs) -> str:
        return "supervisorctl"

    @override
    def command(
        self,
        config_file: str | None = None,
        server_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
    ) -> StringCommand:
        supervisorctl_command = _make_supervisorctl_command(
            config_file=config_file,
            server_url=server_url,
            username=username,
            password=password,
        )

        # status exits non-zero when any process is not RUNNING (supervisor 4.x),
        # which is an expected state rather than an error
        return StringCommand(supervisorctl_command, "status", "||", "true")

    @override
    def process(self, output: list[str]) -> dict[str, bool | None]:
        processes: dict[str, bool | None] = {}

        for line in output:
            parts = line.split()
            if len(parts) < 2:
                continue

            name, state = parts[0], parts[1]

            if state in RUNNING_STATES:
                processes[name] = True
            elif state in STOPPED_STATES:
                processes[name] = False
            elif state in BROKEN_STATES:
                processes[name] = None
            # any other line (eg connection error text) is ignored

        return processes
