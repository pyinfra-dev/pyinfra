# pyinfra
# File: pyinfra/modules/init.py
# Desc: manage init systems

'''
Manages the state and configuration of init services. Support for:

+ SysVinit (/etc/init.d)
+ BSD init (/etc/rc.d)
+ Upstart
+ Systemctl
'''

from __future__ import unicode_literals

from pyinfra.api import operation

from . import files


def _handle_service_control(
    name, statuses, formatter, running, restarted, reloaded, command
):
    statuses = statuses or {}
    status = statuses.get(name, None)
    commands = []

    # Need running but down
    if running is True and not status:
        commands.append(formatter.format(name, 'start'))

    # Need down but running
    if running is False and status is not False:
        commands.append(formatter.format(name, 'stop'))

    if command and status:
        commands.append(formatter.format(name, command))

    if restarted and status:
        commands.append(formatter.format(name, 'restart'))

    if reloaded:
        commands.append(formatter.format(name, 'reload'))

    return commands


@operation
def d(
    state, host, name,
    running=True, restarted=False, reloaded=False,
    enabled=None, command=None
):
    '''
    Manage the state of SysV Init (/etc/init.d) service scripts.

    + name: name of the service to manage
    + running: whether the service should be running
    + restarted: whether the service should be restarted
    + reloaded: whether the service should be reloaded
    + enabled: whether this service should be enabled/disabled
    + command: command (eg. reload) to run like: ``/etc/init.d/<name> <command>``

    Enabled:
        Because managing /etc/rc.d/X files is a mess, only certain Linux distributions
        support enabling/disabling services:

        + Ubuntu/Debian (``update-rc.d``)
        + CentOS/Fedora/RHEL (``chkconfig``)
        + Gentoo (``rc-update``)

        For other distributions and more granular service control, see the
        ``init.d_enable`` operation.
    '''

    commands = _handle_service_control(
        name, host.fact.initd_status,
        '/etc/init.d/{0} {1}',
        running, restarted, reloaded, command
    )

    if enabled is not None:
        start_links = host.fact.find_links('/etc/rc*.d/S*{0}'.format(name)) or []

        # If no links exist, attempt to enable the service using distro-specific commands
        if enabled is True and not start_links:
            distro = host.fact.linux_distribution.get('name')

            if distro in ('Ubuntu', 'Debian'):
                commands.append('update-rc.d {0} defaults'.format(name))

            elif distro in ('CentOS', 'Fedora', 'Red Hat Enterprise Linux'):
                commands.extend([
                    'chkconfig {0} --add'.format(name),
                    'chkconfig {0} on'.format(name)
                ])

            elif distro == 'Gentoo':
                commands.append('rc-update add {0} default'.format(name))

        # Remove any /etc/rcX.d/<name> start links
        elif enabled is False:
            # No state checking, just blindly remove any that exist
            for link in start_links:
                commands.append('rm -f {0}'.format(link))

    return commands


@operation
def d_enable(
    state, host, name,
    start_priority=20, stop_priority=80,
    start_levels=(2, 3, 4, 5), stop_levels=(0, 1, 6)
):
    '''
    Manually enable /etc/init.d scripts by creating /etc/rcX.d/Y links.

    + name: name of the service to enable
    + start_priority: priority to start the service
    + stop_priority: priority to stop the service
    + start_levels: which runlevels should the service run when enabled
    + stop_levels: which runlevels should the service stop when enabled
    '''

    commands = []

    # Build link list
    links = []

    for level in start_levels:
        links.append('/etc/rc{0}.d/S{1}{2}'.format(level, start_priority, name))

    for level in stop_levels:
        links.append('/etc/rc{0}.d/K{1}{2}'.format(level, stop_priority, name))

    # Ensure all the new links exist
    for link in links:
        commands.extend(
            files.link(state, host, link, '/etc/init.d/{0}'.format(name))
        )

    return commands


@operation
def rc(
    state, host, name,
    running=True, restarted=False, reloaded=False,
    command=None, enabled=None
):
    '''
    Manage the state of BSD init (/etc/rc.d) service scripts.

    + name: name of the service to manage
    + running: whether the service should be running
    + restarted: whether the service should be restarted
    + reloaded: whether the service should be reloaded
    + command: custom command to pass like: ``/etc/rc.d/<name> <command>``
    + enabled: whether this service should be enabled/disabled on boot
    '''

    commands = _handle_service_control(
        name, host.fact.rcd_status,
        '/etc/rc.d/{0} {1}',
        running, restarted, reloaded, command
    )

    # BSD init is simple, just add/remove <name>_enabled="YES"
    if isinstance(enabled, bool):
        commands.extend(files.line(
            state, host,
            '/etc/rc.conf.local',
            '{0}_enable=.*'.format(name),
            replace='{0}_enable="YES"'.format(name),
            present=enabled
        ))

    return commands


@operation
def upstart(
    state, host, name,
    running=True, restarted=False, reloaded=False,
    command=None, enabled=None
):
    '''
    Manage the state of upstart managed services.

    + name: name of the service to manage
    + running: whether the service should be running
    + restarted: whether the service should be restarted
    + reloaded: whether the service should be reloaded
    + command: custom command to pass like: ``/etc/rc.d/<name> <command>``
    + enabled: whether this service should be enabled/disabled on boot

    Enabling/disabling services:
        Upstart jobs define runlevels in their config files - as such there is no way to
        edit/list these without fiddling with the config. So pyinfra simply manages the
        existence of a ``/etc/init/<service>.override`` file, and sets its content to
        "manual" to disable automatic start of services.
    '''

    commands = _handle_service_control(
        name, host.fact.upstart_status,
        'initctl {1} {0}',
        running, restarted, reloaded, command
    )

    # Upstart jobs are setup w/runlevels etc in their config files, so here we just check
    # there's no override file.
    if enabled is True:
        commands.extend(files.file(
            state, host,
            '/etc/init/{0}.override'.format(name),
            present=False
        ))

    # Set the override file to "manual" to disable automatic start
    elif enabled is False:
        commands.append('echo "manual" > /etc/init/{0}.override'.format(name))

    return commands


@operation
def systemd(
    state, host, name,
    running=True, restarted=False, reloaded=False,
    command=None, enabled=None
):
    '''
    Manage the state of systemd managed services.

    + name: name of the service to manage
    + running: whether the service should be running
    + restarted: whether the service should be restarted
    + reloaded: whether the service should be reloaded
    + command: custom command to pass like: ``/etc/rc.d/<name> <command>``
    + enabled: whether this service should be enabled/disabled on boot
    '''

    commands = _handle_service_control(
        name, host.fact.systemd_status,
        'systemctl {1} {0}.service',
        running, restarted, reloaded, command
    )

    if isinstance(enabled, bool):
        is_enabled = host.fact.systemd_enabled.get(name, False)

        # Isn't enabled and want enabled?
        if not is_enabled and enabled is True:
            commands.append('systemctl enable {0}.service'.format(name))

        # Is enabled and want disabled?
        elif is_enabled and enabled is False:
            commands.append('systemctl disable {0}.service'.format(name))

    return commands
