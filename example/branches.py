'''
This example demonstrates pyinfra's ability to run code that has conditional
branches and multiple levels of them.

To test the file is converted correctly:
    pyinfra compile deploy_branches.py

And to execute it:
    pyinfra @vagrant deploy_branches.py
'''

from pyinfra import host
from pyinfra.modules import server

SUDO = True


if 'debian' in host.groups:
    server.shell({'DEBIAN-1'}, 'echo DEBIAN-1')
    server.shell({'DEBIAN-2'}, 'echo DEBIAN-2')


if 'bsd' in host.groups:
    server.shell({'BSD-1'}, 'echo BSD-1')
    server.shell({'BSD-2'}, 'echo BSD-2')

    for i in range(3, 5):
        server.shell({'BSD-{0}'.format(i)}, 'echo BSD-{0}'.format(i))


server.shell({'EVERYONE-1'}, 'echo EVERYONE-1')


if 'bsd' in host.groups:
    server.shell({'BSD_GROUP'}, 'echo BSD_GROUP')


server.shell({'EVERYONE-2'}, 'echo EVERYONE-2')


if host.fact.os == 'OpenBSD':
    server.shell({'OS_OPENBSD'}, 'echo OS_OPENBSD')


distro = host.fact.linux_distribution['name']

if distro in ('Ubuntu', 'Debian'):
    server.shell({'UBUNTU_DEBIAN'}, 'echo UBUNTU_DEBIAN')

elif distro in ('CentOS', 'Fedora'):
    if distro == 'CentOS':
        server.shell({'CENTOS-1'}, 'echo CENTOS-1')
        server.shell({'CENTOS-2'}, 'echo CENTOS-2')
        server.shell({'CENTOS-3'}, 'echo CENTOS-3')
        server.shell({'CENTOS-4'}, 'echo CENTOS-4')

    server.shell({'CENTOS_FEDORA-1'}, 'echo CENTOS_FEDORA-1')

    if distro == 'Fedora':
        server.shell({'FEDORA-1'}, 'echo FEDORA-1')

    server.shell({'CENTOS_FEDORA-2'}, 'echo CENTOS_FEDORA-2')

    if distro == 'CentOS':
        server.shell({'CENTOS-5'}, 'echo CENTOS-5')
        server.shell({'CENTOS-6'}, 'echo CENTOS-6')

if host.fact.os == 'OpenBSD':
    server.shell({'OPENBSD-2'}, 'echo OPENBSD-2')

elif distro == 'Debian':
    server.shell({'DEBIAN-3'}, 'echo DEBIAN-3')
    server.shell({'DEBIAN-4'}, 'echo DEBIAN-4')

server.shell({'EVERYONE-3'}, 'echo EVERYONE-3')
