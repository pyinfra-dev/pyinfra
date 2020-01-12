from pyinfra.modules import init

SUDO = True

init.d(
    {'Restart and enable rsyslog'},
    'rsyslog',
    restarted=True,
    enabled=True,
)

init.d_enable(
    {'Finer control on which runlevels rsyslog should run'},
    'rsyslog',
    start_levels=(3, 4, 5),
    stop_levels=(0, 1, 2, 6),
)

init.service(
    {'Enable open-vm-tools service'},
    'open-vm-tools',
    enabled=True,
)
