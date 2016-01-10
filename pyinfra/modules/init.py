# pyinfra
# File: pyinfra/modules/init.py
# Desc: manage init systems

'''
Manages the state and configuration of init services.
'''

from pyinfra.api.operation import operation


def _handle_service_control(
    formatter, name, status, running, restarted, reloaded, command
):
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
    running=True, restarted=False, reloaded=False, command=None
):
    '''Manage the state of /etc/init.d service scripts.'''

    status = host.initd_status or {}
    status = status.get(name, None)

    return _handle_service_control(
        '/etc/init.d/{0} {1}',
        name, status,
        running=running, restarted=restarted, reloaded=reloaded, command=command
    )


@operation
def rc(
    state, host, name,
    running=True, restarted=False, reloaded=False, command=None
):
    '''Manage the state of /etc/rc.d service scripts.'''

    status = host.rcd_status or {}
    status = status.get(name, None)

    return _handle_service_control(
        '/etc/rc.d/{0} {1}',
        name, status,
        running=running, restarted=restarted, reloaded=reloaded, command=command
    )


@operation
def service(
    state, host, name,
    running=True, restarted=False, reloaded=False, command=None
):
    '''Manage the state of "service" managed services.'''

    status = host.service_status or {}
    status = status.get(name, None)

    return _handle_service_control(
        'service {0} {1}',
        name, status,
        running=running, restarted=restarted, reloaded=reloaded, command=command
    )
