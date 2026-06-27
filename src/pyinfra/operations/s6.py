"""Manage s6-rc services (https://www.skarnet.org/software/s6-rc/)."""

from pyinfra import host
from pyinfra.api import operation
from pyinfra.facts import S6RCStatus

from .util.service import handle_service_control


@operation()
def service(
    service: str,
    running: bool = True,
    restarted: bool = False,
    reloaded: bool = False,
    command: str | None = None,
    enabled: bool | None = None,
    managed: bool = True,
    live: str | None = None,
    servicedir: str = "/etc/sv",
):
    """
    Manage the state of s6-supervised services.

    + service: name of the service to manage
    + running: whether the service should be under an s6-supervise.
    + restarted: whether the service should be restarted (with `s6-rc -d change service && s6-rc -u change service`)
    + reloaded: whether the service should be reloaded by sending a SIGHUP.
    + command: TODO
    + enabled: whether the service should be given an "active" or "usable" prescription
    + live: path to the live state directory, using the compiled-in value by default (which is probably /run/s6-rc).
    +
    """
    # TODO "always" rx, "masked" rx
    # reloaded? that would be service-dependent signal. accept it anyway, implement as SIGHUP
    # TODO statuses argument fact
    yield from handle_service_control(
        host,
        service,
        host.get_fact(S6RCStatus),
        "s6-rc {0} change",
        running,
        restarted,
        reloaded,
        command,
    )

    #host: Host,
    #name: str,
    #statuses: dict[str, bool],
    #formatter: str,
    #running: bool | None = None,
    #restarted: bool | None = None,
    #reloaded: bool | None = None,
    #command: str | None = None,
    #status_argument="status",

    # enable: add it to a set, and commit that set.
    if isinstance(enabled, bool):
        yield StringCommand(f"s6-rc-set-change ")

# running: s6-rc -d/-u change
# restarted: s6-rc -d change && s6-rc -u change
# reloaded: s6-svc -h <servicedir>
