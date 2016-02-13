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

from pyinfra.api.operation import operation


def _handle_service_control(
    name, statuses, formatter, running, restarted, reloaded, command
):
    status = statuses.get(name, None)
    commands = []

    # Need running but down
    if running and not status:
        commands.append(formatter.format(name, 'start'))

    # Need down but running
    if not running and status is not False:
        commands.append(formatter.format(name, 'stop'))

    if restarted:
        commands.append(formatter.format(name, 'restart'))

    if reloaded:
        commands.append(formatter.format(name, 'reload'))

    if command:
        commands.append(formatter.format(name, command))

    return commands


@operation
def d(
    state, host, name,
    running=True, restarted=False, reloaded=False,
    command=None, enabled=None, priority=20,
    start_runlevels=(2, 3, 4, 5), kill_runlevels=(0, 1, 6)
):
    '''
    Manage the state of SysV Init (/etc/init.d) service scripts.

    + name: name of the service to manage
    + running: whether the service should be running
    + restarted: whether the service should be restarted
    + reloaded: whether the service should be reloaded
    + command: custom command to pass like: ``/etc/init.d/<name> <command>``
    + enabled: whether this service should be enabled/disabled at runlevels
    + priority: priority to execute the service
    + start_runlevels: which runlevels should the service run when enabled
    + kill_runlevels: which runlevels should the service stop when enabled

    Enabled, priority & runlevels:
        When enabled is ``True`` both priority and runlevels decide which links to init
        scripts are pushed into ``/etc/rcX.d`` where X is the runlevel. When enabled is
        ``False`` pyinfra removes any links matching the service name from all
        ``/etc/rcX.d`` directories.
    '''

    return _handle_service_control(
        name, host.initd_status,
        '/etc/init.d/{0} {1}',
        running, restarted, reloaded, command
    )


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

    return _handle_service_control(
        name, host.rcs_status,
        '/etc/rc.d/{0} {1}',
        running, restarted, reloaded, command
    )


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
    '''

    return _handle_service_control(
        name, host.upstart_status,
        '{1} {0}',
        running, restarted, reloaded, command
    )


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

    return _handle_service_control(
        name, host.systemd_status,
        'systemctl {1} {0}.service',
        running, restarted, reloaded, command
    )
