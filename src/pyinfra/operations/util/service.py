from __future__ import annotations

from pyinfra.api import Host, QuoteString
from pyinfra.api.command import make_formatted_string_command


def handle_service_control(
    host: Host,
    name: str,
    statuses: dict[str, bool],
    formatter: str,
    running: bool | None = None,
    restarted: bool | None = None,
    reloaded: bool | None = None,
    command: str | None = None,
    status_argument="status",
):
    is_running = statuses.get(name, None)

    # Need down but running
    if running is False:
        if is_running:
            yield make_formatted_string_command(formatter, QuoteString(name), "stop")
        else:
            host.noop("service {0} is stopped".format(name))

    # Need running but down
    if running is True:
        if not is_running:
            yield make_formatted_string_command(formatter, QuoteString(name), "start")
        else:
            host.noop("service {0} is running".format(name))

    # Only restart if the service is already running
    if restarted and is_running:
        yield make_formatted_string_command(formatter, QuoteString(name), "restart")

    # Only reload if the service is already reloaded
    if reloaded and is_running:
        yield make_formatted_string_command(formatter, QuoteString(name), "reload")

    # Always execute arbitrary commands as these may or may not rely on the service
    # being up or down
    if command:
        yield make_formatted_string_command(formatter, QuoteString(name), command)
