from pyinfra import host
from pyinfra.modules import apt, pip, pkg, server, yum

# Global flag - this applies to all operations in this file!
SUDO = True


# Only apply to hosts in the `bsd` group
if 'bsd' in host.groups:
    # OpenBSD packages?
    pkg.packages(
        {'Install Python, Pip & Git with pkg_add'},
        ['py-pip', 'git'],
    )

    # add_pkg does not automatically do this
    server.shell(
        {'Symlink pip to pip2.7'},
        'ln -sf /usr/local/bin/pip2.7 /usr/local/bin/pip',
    )


# Work with facts about the remote host
# Storing this fact to avoid typing it so much (because the example targets a whole bunch
# of distros [& 2 OSs]).
distro = host.fact.linux_distribution['name']

if distro in ('Ubuntu', 'Debian'):
    apt.packages(
        {'Install Pip & Git with apt'},
        ['git', 'python-pip'],
        update=True,
        cache_time=3600,
    )

elif distro in ('CentOS', 'Fedora'):
    if distro == 'CentOS':
        # Both missing in the CentOS 7 Vagrant image
        yum.packages(
            {'Install wget & net-tools with yum'},
            ['wget', 'net-tools'],
        )

        # Manage remote rpm files
        yum.rpm(
            {'Install epel RPM'},
            (
                'https://dl.fedoraproject.org/pub/epel/epel-release-latest-'
                '{{ host.fact.linux_distribution.major }}.noarch.rpm'
            ),
        )

    # yum package manager
    yum.packages(
        {'Install Pip & Git with yum'},
        ['git', 'python-pip'],
    )


# Now that we installed pip, we can use it! Note that this operation will be
# run after all the branches above.
pip.packages(
    {'Install a pip package'},
    'pytask',
)
