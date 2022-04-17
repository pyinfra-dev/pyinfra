"""
Manage OpenRC init services.
"""

from pyinfra import host
from pyinfra.api import operation
from pyinfra.facts.openrc import OpenrcEnabled, OpenrcStatus

from .util.service import handle_service_control


@operation
def service(
    service,
    running=True,
    restarted=False,
    reloaded=False,
    command=None,
    enabled=None,
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

        if enabled and not is_enabled:
            yield "rc-update add {0}".format(service)
            openrc_enabled[service] = True

        if not enabled and is_enabled:
            yield "rc-update del {0}".format(service)
            openrc_enabled[service] = False
