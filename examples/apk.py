from pyinfra import host
from pyinfra.modules import apk

SUDO = True

if host.fact.linux_name == 'Alpine':

    apk.packages(
        {'Install Asterisk and Vim'},
        ['asterisk', 'vim'],
        update=True,
    )
