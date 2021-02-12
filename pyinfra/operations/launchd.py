'''
Manage launchd services.
'''

from __future__ import unicode_literals

from pyinfra.api import operation

from .util.service import handle_service_control


@operation
def service(
    service,
    running=True, restarted=False, command=None,
    state=None, host=None,
):
    '''
    Manage the state of systemd managed services.

    + service: name of the service to manage
    + running: whether the service should be running
    + restarted: whether the service should be restarted
    + command: custom command to pass like: ``launchctl <command> <service>``
    + enabled: whether this service should be enabled/disabled on boot
    '''

    was_running = host.fact.launchd_status.get(service, None)

    yield handle_service_control(
        host,
        service, host.fact.launchd_status,
        'launchctl {1} {0}',
        # No support for restart/reload/command
        running, None, None, None,
    )

    # No restart command, so just stop/start
    if restarted and was_running:
        yield 'launchctl stop {0}'.format(service)
        yield 'launchctl start {0}'.format(service)
