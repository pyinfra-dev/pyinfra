"""
Manage runit services.
"""

from __future__ import annotations

from typing import Optional

from pyinfra import host
from pyinfra.api import operation
from pyinfra.facts.files import File
from pyinfra.facts.runit import RunitManaged, RunitStatus

from .files import file, link
from .util.service import handle_service_control


@operation()
def service(
    service: str,
    running: bool = True,
    restarted: bool = False,
    reloaded: bool = False,
    command: Optional[str] = None,
    enabled: Optional[bool] = None,
    managed: bool = True,
    svdir: str = "/var/service",
    sourcedir: str = "/etc/sv",
):
    """
    Manage the state of runit services.

    + service: name of the service to manage
    + running: whether the service should be running
    + restarted: whether the service should be restarted
    + reloaded: whether the service should be reloaded
    + command: custom command to pass like: ``sv <command> <service>``
    + enabled: whether this service should be enabled/disabled on boot
    + managed: whether runit should manage this service

      For services to be controlled, they first need to be managed by runit by
      adding a symlink to the service in ``SVDIR``.
      By setting ``managed=False`` the symlink will be removed.
      Other options won't have any effect after that.
      Although the ``<service>/down`` file can still be controlled with the
      ``enabled`` option.

    + svdir: alternative ``SVDIR``

      An alternative ``SVDIR`` can be specified. This can be used for user services.

    + sourcedir: where to search for available services

      An alternative directory for available services can be specified.
      Example: ``sourcedir=/etc/sv.local`` for services managed by the administrator.
    """

    was_managed = service in host.get_fact(RunitManaged, service=service, svdir=svdir)
    was_auto = not host.get_fact(File, path="{0}/{1}/down".format(sourcedir, service))

    # Disable autostart for previously unmanaged services.
    #
    # Where ``running=False`` is requested, this prevents one case of briefly
    # starting and stopping the service.
    if not was_managed and managed and was_auto:
        yield from auto._inner(
            service=service,
            auto=False,
            sourcedir=sourcedir,
        )

    yield from manage._inner(
        service=service,
        managed=managed,
        svdir=svdir,
        sourcedir=sourcedir,
    )

    # Service wasn't managed before, so wait for ``runsv`` to start.
    # ``runsvdir`` will check at least every 5 seconds for new services.
    # Wait for at most 10 seconds for the service to be managed, otherwise fail.
    if not was_managed and managed:
        yield from wait_runsv._inner(
            service=service,
            svdir=svdir,
        )

    if isinstance(enabled, bool):
        yield from auto._inner(
            service=service,
            auto=enabled,
            sourcedir=sourcedir,
        )
    else:
        # restore previous state of ``<service>/down``
        yield from auto._inner(
            service=service,
            auto=was_auto,
            sourcedir=sourcedir,
        )

    # Services need to be managed by ``runit`` for the other options to make sense.
    if not managed:
        return

    yield from handle_service_control(
        host,
        service,
        host.get_fact(RunitStatus, service=service, svdir=svdir),
        "SVDIR={0} sv {{1}} {{0}}".format(svdir),
        running,
        restarted,
        reloaded,
        command,
    )


@operation()
def manage(
    service: str,
    managed: bool = True,
    svdir: str = "/var/service",
    sourcedir: str = "/etc/sv",
):
    """
    Manage runit svdir links.

    + service: name of the service to manage
    + managed: whether the link should exist
    + svdir: alternative ``SVDIR``
    + sourcedir: where to search for available services
    """

    yield from link._inner(
        path="{0}/{1}".format(svdir, service),
        target="{0}/{1}".format(sourcedir, service),
        present=managed,
        create_remote_dir=False,
    )


@operation(is_idempotent=False)
def wait_runsv(
    service: str,
    svdir: str = "/var/service",
    timeout: int = 10,
):
    """
    Wait for runsv for ``service`` to be available.

    + service: name of the service to manage
    + svdir: alternative ``SVDIR``
    + timeout: time in seconds to wait
    """

    yield (
        "export SVDIR={0}\n"
        "for i in $(seq {1}); do\n"
        "    sv status {2} > /dev/null && exit 0\n"
        "    sleep 1;\n"
        "done\n"
        "exit 1"
    ).format(svdir, timeout, service)


@operation()
def auto(
    service: str,
    auto: bool = True,
    sourcedir: str = "/etc/sv",
):
    """
    Start service automatically by managing the ``service/down`` file.

    + service: name of the service to manage
    + auto: whether the service should start automatically
    + sourcedir: where to search for available services
    """

    yield from file._inner(
        path="{0}/{1}/down".format(sourcedir, service),
        present=not auto,
        create_remote_dir=False,
    )
