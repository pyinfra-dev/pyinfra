from pyinfra import host
from pyinfra.operations import pkg

SUDO = True

if host.fact.os == 'OpenBSD':

    pkg.packages(
        name='Install Vim and Vim Addon Manager',
        packages=['vim-addon-manager', 'vim'],
    )
