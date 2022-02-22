'''
Manage sysvinit services (``/etc/init.d``).
'''

from pyinfra import host
from pyinfra.api import operation
from pyinfra.facts.files import FindLinks
from pyinfra.facts.server import LinuxDistribution
from pyinfra.facts.sysvinit import InitdStatus

from . import files
from .util.service import handle_service_control


@operation
def service(
    service,
    running=True, restarted=False, reloaded=False,
    enabled=None, command=None,
):
    '''
    Manage the state of SysV Init (/etc/init.d) services.

    + service: name of the service to manage
    + running: whether the service should be running
    + restarted: whether the service should be restarted
    + reloaded: whether the service should be reloaded
    + enabled: whether this service should be enabled/disabled
    + command: command (eg. reload) to run like: ``/etc/init.d/<service> <command>``

    Enabled:
        Because managing /etc/rc.d/X files is a mess, only certain Linux distributions
        support enabling/disabling services:

        + Ubuntu/Debian (``update-rc.d``)
        + CentOS/Fedora/RHEL (``chkconfig``)
        + Gentoo (``rc-update``)

        For other distributions and more granular service control, see the
        ``sysvinit.enable`` operation.

    Example:

    .. code:: python

        sysvinit.service(
            name='Restart and enable rsyslog',
            service='rsyslog',
            restarted=True,
            enabled=True,
        )
    '''

    yield from handle_service_control(
        host,
        service, host.get_fact(InitdStatus),
        '/etc/init.d/{0} {1}',
        running, restarted, reloaded, command,
    )

    if isinstance(enabled, bool):
        start_links = host.get_fact(
            FindLinks,
            path='/etc/rc*.d/S*{0}'.format(service),
            quote_path=False,  # enable path glob matching
        )

        # If no links exist, attempt to enable the service using distro-specific commands
        if enabled is True and not start_links:
            distro = host.get_fact(LinuxDistribution).get('name')
            did_add = False

            if distro in ('Ubuntu', 'Debian'):
                yield 'update-rc.d {0} defaults'.format(service)
                did_add = True

            elif distro in ('CentOS', 'Fedora', 'Red Hat Enterprise Linux'):
                yield 'chkconfig {0} --add'.format(service)
                yield 'chkconfig {0} on'.format(service)
                did_add = True

            elif distro == 'Gentoo':
                yield 'rc-update add {0} default'.format(service)
                did_add = True

            # Add a single start link to the fact if we executed a command
            if did_add:
                start_links.append('/etc/rc0.d/S20{0}'.format(service))

        # Remove any /etc/rcX.d/<service> start links
        elif enabled is False:
            # No state checking, just blindly remove any that exist
            for link in start_links:
                yield 'rm -f {0}'.format(link)
                start_links.remove(link)


@operation
def enable(
    service,
    start_priority=20, stop_priority=80,
    start_levels=(2, 3, 4, 5), stop_levels=(0, 1, 6),
):
    '''
    Manually enable /etc/init.d scripts by creating /etc/rcX.d/Y links.

    + service: name of the service to enable
    + start_priority: priority to start the service
    + stop_priority: priority to stop the service
    + start_levels: which runlevels should the service run when enabled
    + stop_levels: which runlevels should the service stop when enabled

    Example:

    .. code:: python

        init.d_enable(
            name='Finer control on which runlevels rsyslog should run',
            service='rsyslog',
            start_levels=(3, 4, 5),
            stop_levels=(0, 1, 2, 6),
        )
    '''

    # Build link list
    links = []

    for level in start_levels:
        links.append('/etc/rc{0}.d/S{1}{2}'.format(level, start_priority, service))

    for level in stop_levels:
        links.append('/etc/rc{0}.d/K{1}{2}'.format(level, stop_priority, service))

    # Ensure all the new links exist
    for link in links:
        yield from files.link(
            path=link,
            target='/etc/init.d/{0}'.format(service),
        )
