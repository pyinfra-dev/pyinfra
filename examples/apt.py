from pyinfra import host
from pyinfra.operations import apt

SUDO = True

code_name = host.fact.linux_distribution['release_meta'].get('DISTRIB_CODENAME')
print(host.fact.linux_name, code_name)

if host.fact.linux_name in ['Debian', 'Ubuntu']:

    apt.packages(
        name='Install some packages',
        packages=['vim-addon-manager', 'vim', 'software-properties-common', 'wget', 'curl'],
        update=True,
    )

    # NOTE: the bitcoin PPA is no longer supported
    # apt.ppa(
    #     {'Add the Bitcoin ppa'},
    #     'ppa:bitcoin/bitcoin',
    # )
    #
    # apt.packages(
    #     {'Install Bitcoin'},
    #     'bitcoin-qt',
    #     update=True,
    # )

    apt.deb(
        name='Install Chrome via deb',
        src='https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb',
    )

    apt.key(
        name='Install VirtualBox key',
        src='https://www.virtualbox.org/download/oracle_vbox_2016.asc',
    )

    apt.repo(
        name='Install VirtualBox repo',
        src='deb https://download.virtualbox.org/virtualbox/debian {} contrib'.format(code_name),
    )
