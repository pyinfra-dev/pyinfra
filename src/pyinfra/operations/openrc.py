"""
Manage OpenRC init services.
"""

from __future__ import annotations

from pyinfra import host
from pyinfra.api import QuoteString, StringCommand, operation
from pyinfra.facts.openrc import OpenrcEnabled, OpenrcStatus

from .util.service import handle_service_control


@operation()
def service(
    service: str,
    running=True,
    restarted=False,
    reloaded=False,
    command: str | None = None,
    enabled: bool | None = None,
    runlevel="default",
):
    """
    Manage the state of OpenRC services.

    + service: name of the service to manage
    + running: whether the service should be running
    + restarted: whether the service should be restarted
    + reloaded: whether the service should be reloaded
    + command: custom command to pass like: ``rc-service <service> <command>``
    + enabled: whether this service should be enabled/disabled on boot
    + runlevel: runlevel to manage services for
    """

    yield from handle_service_control(
        host,
        service,
        host.get_fact(OpenrcStatus, runlevel=runlevel),
        "rc-service {0} {1}",
        running,
        restarted,
        reloaded,
        command,
    )

    if isinstance(enabled, bool):
        openrc_enabled = host.get_fact(OpenrcEnabled, runlevel=runlevel)
        is_enabled = openrc_enabled.get(service, False)

        if enabled is True:
            if not is_enabled:
                yield StringCommand("rc-update add", QuoteString(service), QuoteString(runlevel))
                openrc_enabled[service] = True
            else:
                host.noop(f"service {service} is enabled")

        if enabled is False:
            if is_enabled:
                yield StringCommand("rc-update del", QuoteString(service), QuoteString(runlevel))
                openrc_enabled[service] = False
            else:
                host.noop(f"service {service} is disabled")
