from pyinfra import host
from pyinfra.modules import apt, python, server

SUDO = True

virtualbox_version = '6.1'


def verify_virtualbox_version(state, host):
    command = '/usr/bin/virtualbox --help'
    status, stdout, stderr = host.run_shell_command(state, command=command, sudo=SUDO)
    assert status is True  # ensure the command executed OK
    # TODO: how to pass version to this callback?
    # TODO: how to return values from callback?
    if virtualbox_version not in str(stdout):
        raise Exception('`{}` did not work as expected.stdout:{} stderr:{}'.format(
            command, stdout, stderr))


if host.fact.linux_name == 'Ubuntu':
    code_name = host.fact.linux_distribution['release_meta'].get('DISTRIB_CODENAME')
    print(host.fact.linux_name, code_name)

    apt.packages(
        {'Install packages'},
        ['wget'],
        update=True,
    )

    apt.key(
        {'Install VirtualBox key'},
        'https://www.virtualbox.org/download/oracle_vbox_2016.asc',
    )

    apt.repo(
        {'Install VirtualBox repo'},
        'deb https://download.virtualbox.org/virtualbox/debian {} contrib'.format(code_name),
    )

    # install kernel headers
    # Note: host.fact.os_version is the same as `uname -r` (ex: '4.15.0-72-generic')
    apt.packages(
        {
            'Install VirtualBox version {} and '
            'kernel headers for {}'.format(virtualbox_version, host.fact.os_version),
        },
        [
            'virtualbox-{}'.format(virtualbox_version),
            'linux-headers-{}'.format(host.fact.os_version),
        ],
        update=True,
    )

    server.shell(
        {'Run vboxconfig which will stop/start VirtualBox services and build kernel modules'},
        '/sbin/vboxconfig',
    )

    # TODO: how would I pass version=virtualbox_version to this callback?
    python.call(
        {'Verify VirtualBox version'},
        verify_virtualbox_version,
    )
