from pyinfra import host
from pyinfra.modules import apt

SUDO = True

# Note: Using linux_distribution fact so running from docker
# will show valid name, otherwise could just use host.fact.linux_name
linux = host.fact.linux_distribution
linux_name = linux.get('name', '')
print(linux_name)

if linux_name in ['Debian', 'Ubuntu']:

    apt.packages(
        {'Install Vim and Vim Addon Manager'},
        ['vim-addon-manager', 'vim'],
        update=True,
    )

    apt.ppa(
        {'Add the Bitcoin ppa'},
        'ppa:bitcoin/bitcoin',
    )

    # typically after adding a ppk, you want to update
    apt.update()

    # but you could just include the update in the apt install step
    # like this:
    apt.packages(
        {'Install Bitcoin'},
        'bitcoin-qt',
        update=True,
    )
