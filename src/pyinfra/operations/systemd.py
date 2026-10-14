"""
Manage systemd services.
"""

from __future__ import annotations

from pyinfra import host
from pyinfra.api import QuoteString, StringCommand, operation
from pyinfra.api.exceptions import OperationValueError
from pyinfra.facts.systemd import (
    SystemdEnabled,
    SystemdMasked,
    SystemdStatus,
    _make_systemctl_cmd,
)

from .util.service import handle_service_control


@operation(is_idempotent=False)
def daemon_reload(user_mode=False, machine: str | None = None, user_name: str | None = None):
    """
    Reload the systemd daemon to read unit file changes.

    + user_mode: whether to use per-user systemd (systemctl --user) or not
    + machine: the machine name to connect to
    + user_name: connect to a specific user's systemd session
    """

    systemctl_cmd = _make_systemctl_cmd(
        user_mode=user_mode,
        machine=machine,
        user_name=user_name,
    )

    yield StringCommand(systemctl_cmd, "daemon-reload")


_daemon_reload = daemon_reload._inner  # noqa: E305


@operation()
def service(
    service: str,
    running=True,
    restarted=False,
    reloaded=False,
    command: str | None = None,
    enabled: bool | None = None,
    masked: bool | None = None,
    daemon_reload=False,
    user_mode=False,
    machine: str | None = None,
    user_name: str | None = None,
):
    """
    Manage the state of systemd managed units.

    + service: name of the systemd unit to manage
    + running: whether the unit should be running
    + restarted: whether the unit should be restarted
    + reloaded: whether the unit should be reloaded
    + command: custom command to pass like: ``/etc/rc.d/<name> <command>``
    + enabled: whether this unit should be enabled/disabled on boot
    + masked: whether this unit should be masked/unmasked (a masked unit cannot be started)
    + daemon_reload: reload the systemd daemon to read updated unit files
    + user_mode: whether to use per-user systemd (systemctl --user) or not
    + machine: the machine name to connect to
    + user_name: connect to a specific user's systemd session

    **Examples:**

    .. code:: python

        from pyinfra.operations import systemd
        systemd.service(
            name="Restart and enable the dnsmasq service",
            service="dnsmasq.service",
            running=True,
            restarted=True,
            enabled=True,
        )

        systemd.service(
            name="Enable logrotate timer",
            service="logrotate.timer",
            running=True,
            enabled=True,
        )

        systemd.service(
            name="Stop and mask the bluetooth service",
            service="bluetooth.service",
            running=False,
            masked=True,
        )

    """

    if masked is True:
        if running is True:
            raise OperationValueError("A masked unit cannot be running, set `running=False`")
        if enabled is True:
            raise OperationValueError("A masked unit cannot be enabled")

    systemctl_cmd = _make_systemctl_cmd(
        user_mode=user_mode,
        machine=machine,
        user_name=user_name,
    )

    if not service.endswith(
        (
            ".service",
            ".socket",
            ".device",
            ".mount",
            ".automount",
            ".swap",
            ".target",
            ".path",
            ".timer",
            ".slice",
            ".scope",
        )
    ):
        service = f"{service}.service"

    if daemon_reload:
        yield from _daemon_reload(
            user_mode=user_mode,
            machine=machine,
            user_name=user_name,
        )

    is_masked = False
    if isinstance(masked, bool):
        systemd_masked = host.get_fact(
            SystemdMasked,
            user_mode=user_mode,
            machine=machine,
            user_name=user_name,
            services=[service],
        )
        is_masked = systemd_masked.get(service, False)

    # Unmask before any start/enable, since masked units cannot be started
    if is_masked and masked is False:
        yield StringCommand(systemctl_cmd, "unmask", QuoteString(service))

    yield from handle_service_control(
        host,
        service,
        host.get_fact(
            SystemdStatus,
            user_mode=user_mode,
            machine=machine,
            user_name=user_name,
            services=[service],
        ),
        " ".join([systemctl_cmd.get_raw_value(), "{1}", "{0}"]),
        running,
        restarted,
        reloaded,
        command,
    )

    if isinstance(enabled, bool):
        systemd_enabled = host.get_fact(
            SystemdEnabled,
            user_mode=user_mode,
            machine=machine,
            user_name=user_name,
            services=[service],
        )
        is_enabled = systemd_enabled.get(service, False)

        # Isn't enabled and want enabled?
        if not is_enabled and enabled is True:
            yield StringCommand(systemctl_cmd, "enable", QuoteString(service))

        # Is enabled and want disabled?
        elif is_enabled and enabled is False:
            yield StringCommand(systemctl_cmd, "disable", QuoteString(service))

    if not is_masked and masked is True:
        yield StringCommand(systemctl_cmd, "mask", QuoteString(service))
