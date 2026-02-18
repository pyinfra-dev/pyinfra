from __future__ import annotations

import shlex

from pyinfra.api import Host


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
    status_command: str | None = None,
    status_command_actions: tuple[str, ...] = ("start", "restart", "reload"),
):
    is_running = statuses.get(name, None)
    quoted_name = shlex.quote(name)

    def _format_status_command() -> str | None:
        if not status_command:
            return None
        return status_command.format(service=quoted_name)

    def _format_action_command(action: str) -> str:
        action_command = formatter.format(quoted_name, action)
        status_cmd = _format_status_command()
        if status_cmd and action in status_command_actions:
            return "{0} && {1}".format(action_command, status_cmd)
        return action_command

    # Need down but running
    if running is False:
        if is_running:
            yield _format_action_command("stop")
        else:
            host.noop("service {0} is stopped".format(name))

    # Need running but down
    if running is True:
        if not is_running:
            yield _format_action_command("start")
        else:
            host.noop("service {0} is running".format(name))

    # Only restart if the service is already running
    if restarted and is_running:
        yield _format_action_command("restart")

    # Only reload if the service is already reloaded
    if reloaded and is_running:
        yield _format_action_command("reload")

    # Always execute arbitrary commands as these may or may not rely on the service
    # being up or down
    if command:
        yield _format_action_command(command)
