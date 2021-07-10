from pyinfra import host
from pyinfra.facts.server import LinuxName
from pyinfra.operations import apk

SUDO = True

if host.get_fact(LinuxName) == 'Alpine':

    apk.packages(
        name='Install Asterisk and Vim',
        packages=['asterisk', 'vim'],
        update=True,
    )
