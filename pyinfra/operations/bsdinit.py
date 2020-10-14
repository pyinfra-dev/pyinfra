'''
Manage BSD init services (``/etc/rc.d``).
'''

from __future__ import unicode_literals

from pyinfra.api import operation

from . import files
from .util.service import handle_service_control


@operation
def service(
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

    yield handle_service_control(
        host,
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
