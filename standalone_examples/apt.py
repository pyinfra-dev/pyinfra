from pyinfra import host
from pyinfra.modules import apt

SUDO = True

if host.fact.linux_name in ['Debian', 'Ubuntu']:

    apt.packages(
        {'Install Vim and Vim Addon Manager'},
        ['vim-addon-manager', 'vim'],
        update=True,
    )
