from pyinfra import host
from pyinfra.modules import apt

SUDO = True

# Note: Using linux_distribution fact so running from docker
# will show valid name, otherwise could just use host.fact.linux_name
ld = host.fact.linux_distribution
#print(ld)
linux_name = ld.get('name', '')
#rm = ld.get('release_meta', '')
#code_name = rm.get('DISTRIB_CODENAME', '')
#print(linux_name, code_name)

if linux_name in ['Debian', 'Ubuntu']:

    apt.packages(
        {'Install some packages'},
        ['vim-addon-manager', 'vim', 'software-properties-common', 'wget'],
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
        'deb https://download.virtualbox.org/virtualbox/debian {{ code_name }} contrib',
    )
