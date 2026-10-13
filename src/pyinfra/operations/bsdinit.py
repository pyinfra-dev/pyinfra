"""
Manage BSD init services (``/etc/rc.d``, ``/usr/local/etc/rc.d``).
"""

from __future__ import annotations

from pyinfra import host
from pyinfra.api import QuoteString, StringCommand, operation
from pyinfra.facts.bsdinit import RcdEnabled, RcdStatus
from pyinfra.facts.server import Os

from . import files
from .util.service import handle_service_control


def _handle_openbsd_enabled(service: str, enabled: bool):
    enabled_services = host.get_fact(RcdEnabled)
    is_enabled = enabled_services.get(service, False)

    if enabled is True:
        if not is_enabled:
            yield StringCommand("rcctl enable", QuoteString(service))
            enabled_services[service] = True
        else:
            host.noop(f"service {service} is enabled")

    if enabled is False:
        if is_enabled:
            yield StringCommand("rcctl disable", QuoteString(service))
            enabled_services[service] = False
        else:
            host.noop(f"service {service} is disabled")


@operation()
def service(
    service: str,
    running=True,
    restarted=False,
    reloaded=False,
    command: str | None = None,
    enabled: bool | None = None,
):
    """
    Manage the state of BSD init services.

    + service: name of the service to manage
    + running: whether the service should be running
    + restarted: whether the service should be restarted
    + reloaded: whether the service should be reloaded
    + command: custom command to pass like: ``/etc/rc.d/<service> <command>``
    + enabled: whether this service should be enabled/disabled on boot
    """

    os = host.get_fact(Os)
    status_argument = "status"
    command_formatter = "test -e /etc/rc.d/{0} && /etc/rc.d/{0} {1} || /usr/local/etc/rc.d/{0} {1}"
    if os == "OpenBSD":
        status_argument = "check"
        command_formatter = "rcctl {1} {0}"

        if enabled is True:
            yield from _handle_openbsd_enabled(service, enabled)

    yield from handle_service_control(
        host,
        service,
        host.get_fact(RcdStatus),
        command_formatter,
        running,
        restarted,
        reloaded,
        command,
        status_argument=status_argument,
    )

    if os == "OpenBSD":
        if enabled is False:
            yield from _handle_openbsd_enabled(service, enabled)
        return

    # BSD init is simple, just add/remove <service>_enabled="YES"
    if isinstance(enabled, bool):
        yield from files.line._inner(
            path="/etc/rc.conf.local",
            line=f"^{service}_enable=",
            replace=f'{service}_enable="YES"',
            present=enabled,
        )
