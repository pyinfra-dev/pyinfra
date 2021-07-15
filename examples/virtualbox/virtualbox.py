from pyinfra import host
from pyinfra.facts.server import LinuxDistribution, LinuxName, OsVersion
from pyinfra.operations import apt, python, server

SUDO = True

virtualbox_version = '6.1'


def verify_virtualbox_version(state, host, version):
    command = '/usr/bin/virtualbox --help'
    status, stdout, stderr = host.run_shell_command(state, command=command, sudo=SUDO)
    assert status is True  # ensure the command executed OK
    if version not in str(stdout):
        raise Exception('`{}` did not work as expected.stdout:{} stderr:{}'.format(
            command, stdout, stderr))


if host.get_fact(LinuxName) == 'Ubuntu':
    code_name = host.get_fact(LinuxDistribution)['release_meta'].get('DISTRIB_CODENAME')

    apt.packages(
        name='Install packages',
        packages=['wget'],
        update=True,
    )

    apt.key(
        name='Install VirtualBox key',
        src='https://www.virtualbox.org/download/oracle_vbox_2016.asc',
    )

    apt.repo(
        name='Install VirtualBox repo',
        src='deb https://download.virtualbox.org/virtualbox/debian {} contrib'.format(code_name),
    )

    # install kernel headers
    # Note: host.get_fact(OsVersion) is the same as `uname -r` (ex: '4.15.0-72-generic')
    apt.packages(
        {
            'Install VirtualBox version {} and '
            'kernel headers for {}'.format(virtualbox_version, host.get_fact(OsVersion)),
        },
        [
            'virtualbox-{}'.format(virtualbox_version),
            'linux-headers-{}'.format(host.get_fact(OsVersion)),
        ],
        update=True,
    )

    server.shell(
        name='Run vboxconfig which will stop/start VirtualBox services and build kernel modules',
        commands='/sbin/vboxconfig',
    )

    python.call(
        name='Verify VirtualBox version',
        function=verify_virtualbox_version,
        version=virtualbox_version,
    )
