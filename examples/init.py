from pyinfra.operations import init

SUDO = True

init.d(
    name='Restart and enable rsyslog',
    service='rsyslog',
    restarted=True,
    enabled=True,
)

init.d_enable(
    name='Finer control on which runlevels rsyslog should run',
    service='rsyslog',
    start_levels=(3, 4, 5),
    stop_levels=(0, 1, 2, 6),
)

init.service(
    name='Enable open-vm-tools service',
    service='open-vm-tools',
    enabled=True,
)
