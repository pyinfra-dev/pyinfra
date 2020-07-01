from pyinfra import host
from pyinfra.operations import apk

SUDO = True

if host.fact.linux_name == 'Alpine':

    apk.packages(
        name='Install Asterisk and Vim',
        packages=['asterisk', 'vim'],
        update=True,
    )
