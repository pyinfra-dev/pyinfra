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
    server.shell('echo DEBIAN-1')
    server.shell('echo DEBIAN-2')


if 'bsd' in host.groups:
    server.shell('echo BSD-1')
    server.shell('echo BSD-2')
    server.shell('echo BSD-3')
    server.shell('echo BSD-4')
    server.shell('echo BSD-5')
    server.shell('echo BSD-6')
    server.shell('echo BSD-7')


server.shell('echo EVERYONE-0')


if 'bsd' in host.groups:
    server.shell('echo BSD_GROUP')


server.shell('echo EVERYONE-1')


if host.fact.os == 'OpenBSD':
    server.shell('echo OS_OPENBSD')


distro = host.fact.linux_distribution['name']

if distro in ('Ubuntu', 'Debian'):
    server.shell('echo UBUNTU_DEBIAN')

elif distro in ('CentOS', 'Fedora'):
    if distro == 'CentOS':
        server.shell('echo CENTOS')
        server.shell('echo CENTOS-2')
        server.shell('echo CENTOS-3')
        server.shell('echo CENTOS-4')

    server.shell('echo CENTOS_FEDORA')

    if distro == 'Fedora':
        server.shell('echo FEDORA')

    server.shell('echo CENTOS_FEDORA-2')

    if distro == 'CentOS':
        server.shell('echo CENTOS-5')
        server.shell('echo CENTOS-6')

if host.fact.os == 'OpenBSD':
    server.shell('echo OPENBSD-2')

elif distro == 'Debian':
    server.shell('echo DEBIAN')
    server.shell('echo DEBIAN-2')

server.shell('echo EVERYONE-2')
