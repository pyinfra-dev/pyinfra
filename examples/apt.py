from pyinfra import host
from pyinfra.modules import apt

SUDO = True

code_name = host.fact.linux_distribution['release_meta'].get('DISTRIB_CODENAME')
print(host.fact.linux_name, code_name)

if host.fact.linux_name in ['Debian', 'Ubuntu']:

    apt.packages(
        {'Install some packages'},
        ['vim-addon-manager', 'vim', 'software-properties-common', 'wget', 'curl'],
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

    apt.deb(
        {'Install Chrome via deb'},
        'https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb',
    )

    apt.key(
        {'Install VirtualBox key'},
        'https://www.virtualbox.org/download/oracle_vbox_2016.asc',
    )

    apt.repo(
        {'Install VirtualBox repo'},
        'deb https://download.virtualbox.org/virtualbox/debian {} contrib'.format(code_name),
    )
