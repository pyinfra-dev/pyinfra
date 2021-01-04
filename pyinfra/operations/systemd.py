'''
Manage systemd services.
'''

from __future__ import unicode_literals

from pyinfra.api import operation

from .util.service import handle_service_control


@operation
def daemon_reload(user_mode=False, state=None, host=None):
    '''
    Reload the systemd daemon to read unit file changes.

    + user_mode: whether to use per-user systemd (systemctl --user) or not
    '''

    systemctl_cmd = 'systemctl --user' if user_mode else 'systemctl'
    yield '{0} daemon-reload'.format(systemctl_cmd)

_daemon_reload = daemon_reload  # noqa: E305


@operation
def service(
    service,
    running=True, restarted=False, reloaded=False,
    command=None, enabled=None, daemon_reload=False,
    user_mode=False, state=None, host=None,
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
    + user_mode: whether to use per-user systemd (systemctl --user) or not

    Example:

    .. code:: python

        systemd.service(
            name='Restart and enable the dnsmasq service',
            service='dnsmasq.service',
            running=True,
            restarted=True,
            enabled=True,
        )

        systemd.service(
            name='Enable logrotate timer',
            service='logrotate.timer',
            running=True,
            enabled=True,
        )

    '''

    systemctl_cmd = 'systemctl --user' if user_mode else 'systemctl'

    if '.' not in service:
        service = '{0}.service'.format(service)

    if daemon_reload:
        yield _daemon_reload(user_mode=user_mode, state=state, host=host)

    yield handle_service_control(
        host,
        service, host.fact.systemd_status,
        ' '.join([systemctl_cmd, '{1}', '{0}']),
        running, restarted, reloaded, command,
    )

    if isinstance(enabled, bool):
        is_enabled = host.fact.systemd_enabled.get(service, False)

        # Isn't enabled and want enabled?
        if not is_enabled and enabled is True:

            yield ' '.join([systemctl_cmd, 'enable', '{0}']).format(service)
            host.fact.systemd_enabled[service] = True

        # Is enabled and want disabled?
        elif is_enabled and enabled is False:
            yield ' '.join([systemctl_cmd, 'disable', '{0}']).format(service)
            host.fact.systemd_enabled[service] = False
