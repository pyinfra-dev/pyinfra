"""
Manage FreeBSD services.
"""

from __future__ import annotations

from typing_extensions import List, Optional, Union

from pyinfra import host
from pyinfra.api import QuoteString, StringCommand, operation
from pyinfra.api.exceptions import OperationValueError
from pyinfra.facts.freebsd import ServiceScript, ServiceStatus

SRV_STARTED: str = "started"
SRV_STOPPED: str = "stopped"
SRV_RESTARTED: str = "restarted"
SRV_RELOADED: str = "reloaded"
SRV_CUSTOM: str = "custom"


@operation()
def service(
    srvname: str,
    jail: Optional[str] = None,
    srvstate: str = SRV_STARTED,
    command: Optional[Union[str, List[str]]] = None,
    environment: Optional[List[str]] = None,
    verbose: bool = False,
):
    """
    Control (start/stop/etc.) ``rc(8)`` scripts.

    + srvname: Service.
    + jail: See ``-j`` in ``service(8)``.
    + srvstate: Desire state of the service.
    + command: When ``srvstate`` is ``custom``, the command to execute.
    + environment: See ``-E`` in ``service(8)``.
    + verbose: See ``-v`` in ``service(8)``.

    States:
        There are a few states you can use to manipulate the service:

        - started: The service must be started.
        - stopped: The service must be stopped.
        - restarted: The service must be restarted.
        - reloaded: The service must be reloaded.
        - custom: Run a custom command for this service.

    **Examples:**

    .. code:: python

        # Start a service.
        service.service(
            "beanstalkd",
            srvstate="started"
        )

        # Execute a custom command.
        service.service(
            "sopel",
            srvstate="custom",
            command="configure"
        )
    """

    if not host.get_fact(ServiceScript, srvname=srvname, jail=jail):
        host.noop(f"Cannot find rc(8) script '{srvname}'")
        return

    args: List[Union[str, "QuoteString"]] = []

    args.append("service")

    if verbose:
        args.append("-v")

    if jail is not None:
        args.extend(["-j", QuoteString(jail)])

    if environment is not None:
        for env_var in environment:
            args.extend(["-E", QuoteString(env_var)])

    if srvstate == SRV_STARTED:
        if host.get_fact(ServiceStatus, srvname=srvname, jail=jail):
            host.noop(f"Service '{srvname}' already started")
            return

        args.extend([QuoteString(srvname), "start"])

    elif srvstate == SRV_STOPPED:
        if not host.get_fact(ServiceStatus, srvname=srvname, jail=jail):
            host.noop(f"Service '{srvname}' already stopped")
            return

        args.extend([QuoteString(srvname), "stop"])
    elif srvstate == SRV_RESTARTED:
        args.extend([QuoteString(srvname), "restart"])

    elif srvstate == SRV_RELOADED:
        args.extend([QuoteString(srvname), "reload"])

    elif srvstate == SRV_CUSTOM:
        args.append(QuoteString(srvname))

        if command is not None:
            if isinstance(command, str):
                command = [command]

            args.extend([QuoteString(c) for c in command])

    else:
        raise OperationValueError(f"Invalid service command: {srvstate}")

    yield StringCommand(*args)
