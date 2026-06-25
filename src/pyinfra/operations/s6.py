"""Manage s6-rc services (https://www.skarnet.org/software/s6-rc/)."""

from pyinfra import host
from pyinfra.api import operation

from .util.service import handle_service_control

@operation()
def service():
    """
    Manage the state of s6-supervised services.

    + service:
    + running:
    + restarted:
    + reloaded:
    + enabled:
    """
    # reloaded? that would be service-dependent signal. accept it anyway, implement as SIGHUP
    # TODO statuses argument fact
    yield from handle_service_control(
            host,
            service,
            host.get_fact(S6Status) ,
            "",

            )
