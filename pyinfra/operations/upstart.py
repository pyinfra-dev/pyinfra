"""
Manage upstart services.
"""

from io import StringIO

from pyinfra import host
from pyinfra.api import operation
from pyinfra.facts.upstart import UpstartStatus

from . import files
from .util.service import handle_service_control


@operation
def service(
    service,
    running=True,
    restarted=False,
    reloaded=False,
    command=None,
    enabled=None,
):
    """
    Manage the state of upstart managed services.

    + service: name of the service to manage
    + running: whether the service should be running
    + restarted: whether the service should be restarted
    + reloaded: whether the service should be reloaded
    + command: custom command to pass like: ``/etc/rc.d/<service> <command>``
    + enabled: whether this service should be enabled/disabled on boot

    Enabling/disabling services:
        Upstart jobs define runlevels in their config files - as such there is no way to
        edit/list these without fiddling with the config. So pyinfra simply manages the
        existence of a ``/etc/init/<service>.override`` file, and sets its content to
        "manual" to disable automatic start of services.
    """

    yield from handle_service_control(
        host,
        service,
        host.get_fact(UpstartStatus),
        "initctl {1} {0}",
        running,
        restarted,
        reloaded,
        command,
    )

    # Upstart jobs are setup w/runlevels etc in their config files, so here we just check
    # there's no override file.
    if enabled is True:
        yield from files.file(
            "/etc/init/{0}.override".format(service),
            present=False,
        )

    # Set the override file to "manual" to disable automatic start
    elif enabled is False:
        file = StringIO("manual\n")
        yield from files.put(
            src=file,
            dest="/etc/init/{0}.override".format(service),
        )
