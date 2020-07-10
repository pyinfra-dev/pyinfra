'''
Manages the state and configuration of init services. Support for:

+ SysVinit (/etc/init.d)
+ BSD init (/etc/rc.d)
+ Upstart
+ Systemctl
'''

from __future__ import unicode_literals

from pyinfra.api import operation, OperationError

from . import files


def _handle_service_control(
    name, statuses, formatter, running, restarted, reloaded, command,
    status_argument='status',
):
    statuses = statuses or {}
    status = statuses.get(name, None)

    # If we don't know the status, we need to check if it's up before starting
    # and/or restarting/reloading
    if status is None:
        yield '''
            # If the service is running
            if {status_command}; then
                {stop_command}
                {restart_command}
                {reload_command}

            # If the service is not running, we just start it (no re[start|load])
            else
                {start_command}
            fi
        '''.format(
            status_command=formatter.format(name, status_argument),
            start_command=(
                formatter.format(name, 'start')
                if running is True else 'true'
            ),
            stop_command=(
                formatter.format(name, 'stop')
                if running is False else 'true'
            ),
            restart_command=(
                formatter.format(name, 'restart')
                if restarted else 'true'
            ),
            reload_command=(
                formatter.format(name, 'reload')
                if reloaded else 'true'
            ),
        )

    else:
        # Need down but running
        if running is False and status:
            yield formatter.format(name, 'stop')

        # Need running but down
        if running is True and not status:
            yield formatter.format(name, 'start')

        # Only restart if the service is already running
        if restarted and status:
            yield formatter.format(name, 'restart')

        # Only reload if the service is already reloaded
        if reloaded and status:
            yield formatter.format(name, 'reload')

    # Always execute arbitrary commands as these may or may not rely on the service
    # being up or down
    if command:
        yield formatter.format(name, command)


@operation
def d(
    service,
    running=True, restarted=False, reloaded=False,
    enabled=None, command=None,
    state=None, host=None,
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
        ``init.d_enable`` operation.

    Example:

    .. code:: python

        init.d(
            name='Restart and enable rsyslog',
            service='rsyslog',
            restarted=True,
            enabled=True,
        )
    '''

    yield _handle_service_control(
        service, host.fact.initd_status,
        '/etc/init.d/{0} {1}',
        running, restarted, reloaded, command,
    )

    if isinstance(enabled, bool):
        start_links = host.fact.find_links('/etc/rc*.d/S*{0}'.format(service)) or []

        # If no links exist, attempt to enable the service using distro-specific commands
        if enabled is True and not start_links:
            distro = host.fact.linux_distribution.get('name')

            if distro in ('Ubuntu', 'Debian'):
                yield 'update-rc.d {0} defaults'.format(service)

            elif distro in ('CentOS', 'Fedora', 'Red Hat Enterprise Linux'):
                yield 'chkconfig {0} --add'.format(service)
                yield 'chkconfig {0} on'.format(service)

            elif distro == 'Gentoo':
                yield 'rc-update add {0} default'.format(service)

        # Remove any /etc/rcX.d/<service> start links
        elif enabled is False:
            # No state checking, just blindly remove any that exist
            for link in start_links:
                yield 'rm -f {0}'.format(link)


@operation
def d_enable(
    service,
    start_priority=20, stop_priority=80,
    start_levels=(2, 3, 4, 5), stop_levels=(0, 1, 6),
    state=None, host=None,
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
        yield files.link(
            path=link,
            target='/etc/init.d/{0}'.format(service),
            state=state, host=host,
        )


@operation
def rc(
    service,
    running=True, restarted=False, reloaded=False,
    command=None, enabled=None,
    state=None, host=None,
):
    '''
    Manage the state of BSD init (/etc/rc.d) services.

    + service: name of the service to manage
    + running: whether the service should be running
    + restarted: whether the service should be restarted
    + reloaded: whether the service should be reloaded
    + command: custom command to pass like: ``/etc/rc.d/<service> <command>``
    + enabled: whether this service should be enabled/disabled on boot
    '''

    yield _handle_service_control(
        service, host.fact.rcd_status,
        '/etc/rc.d/{0} {1}',
        running, restarted, reloaded, command,
        status_argument='check',
    )

    # BSD init is simple, just add/remove <service>_enabled="YES"
    if isinstance(enabled, bool):
        yield files.line(
            '/etc/rc.conf.local',
            '^{0}_enable='.format(service),
            replace='{0}_enable="YES"'.format(service),
            present=enabled,
            state=state, host=host,
        )


@operation
def upstart(
    service,
    running=True, restarted=False, reloaded=False,
    command=None, enabled=None,
    state=None, host=None,
):
    '''
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
    '''

    yield _handle_service_control(
        service, host.fact.upstart_status,
        'initctl {1} {0}',
        running, restarted, reloaded, command,
    )

    # Upstart jobs are setup w/runlevels etc in their config files, so here we just check
    # there's no override file.
    if enabled is True:
        yield files.file(
            '/etc/init/{0}.override'.format(service),
            present=False,
            state=state, host=host,
        )

    # Set the override file to "manual" to disable automatic start
    elif enabled is False:
        yield 'echo "manual" > /etc/init/{0}.override'.format(service)


@operation
def systemd(
    service,
    running=True, restarted=False, reloaded=False,
    command=None, enabled=None, daemon_reload=False,
    state=None, host=None,
):
    '''
    Manage the state of systemd managed units.

    + service: name of the systemd unit to manage
    + running: whether the unit should be running
    + restarted: whether the unit should be restarted
    + reloaded: whether the unit should be reloaded
    + command: custom command to pass like: ``/etc/rc.d/<name> <command>``
    + enabled: whether this unit should be enabled/disabled on boot
    + daemon_reload: reload the systemd daemon to read updated unit files

    Example:

    .. code:: python

        init.systemd(
            name='Restart and enable the dnsmasq service',
            service='dnsmasq.service',
            running=True,
            restarted=True,
            enabled=True,
        )

        init.systemd(
            name='Enable logrotate timer',
            service='logrotate.timer',
            running=True,
            enabled=True,
        )

    '''

    if '.' not in service:
        service = '{0}.service'.format(service)

    if daemon_reload:
        yield 'systemctl daemon-reload'

    yield _handle_service_control(
        service, host.fact.systemd_status,
        'systemctl {1} {0}',
        running, restarted, reloaded, command,
    )

    if isinstance(enabled, bool):
        is_enabled = host.fact.systemd_enabled.get(service, False)

        # Isn't enabled and want enabled?
        if not is_enabled and enabled is True:
            yield 'systemctl enable {0}'.format(service)

        # Is enabled and want disabled?
        elif is_enabled and enabled is False:
            yield 'systemctl disable {0}'.format(service)


@operation
def launchd(
    service,
    running=True, restarted=False, command=None,
    state=None, host=None,
):
    '''
    Manage the state of systemd managed services.

    + service: name of the service to manage
    + running: whether the service should be running
    + restarted: whether the service should be restarted
    + command: custom command to pass like: ``/etc/rc.d/<name> <command>``
    + enabled: whether this service should be enabled/disabled on boot
    + daemon_reload: reload the systemd daemon to read updated unit files
    '''

    yield _handle_service_control(
        service, host.fact.launchd_status,
        'launchctl {1} {0}',
        # No support for restart/reload/command
        running, None, None, None,
    )

    # No restart command, so just stop/start
    is_running = host.fact.launchd_status.get(service, None)
    if restarted and is_running:
        yield 'launchctl stop {0}'.format(service)
        yield 'launchctl start {0}'.format(service)


@operation
def service(*args, **kwargs):
    '''
    Manage the state of services. This command checks for the presence of all the
    init systems pyinfra can handle and executes the relevant operation. See init
    system sepcific operation for arguments.

    Example:

    .. code:: python

        init.service(
            name='Enable open-vm-tools service',
            service='open-vm-tools',
            enabled=True,
        )
    '''

    host = kwargs['host']

    if host.fact.which('systemctl'):
        yield systemd(*args, **kwargs)
        return

    if host.fact.which('initctl'):
        yield upstart(*args, **kwargs)
        return

    if host.fact.directory('/etc/init.d'):
        yield d(*args, **kwargs)
        return

    if host.fact.directory('/etc/rc.d'):
        yield rc(*args, **kwargs)
        return

    raise OperationError((
        'No init system found '
        '(no systemctl, initctl, /etc/init.d or /etc/rc.d found)'
    ))
