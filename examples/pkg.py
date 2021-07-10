from pyinfra import host
from pyinfra.facts.server import Os
from pyinfra.operations import pkg

SUDO = True

if host.get_fact(Os) == 'OpenBSD':

    pkg.packages(
        name='Install Vim and Vim Addon Manager',
        packages=['vim-addon-manager', 'vim'],
    )
