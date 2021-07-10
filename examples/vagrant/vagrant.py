from pyinfra import host
from pyinfra.facts.server import LinuxName
from pyinfra.operations import apt, files, python, server

SUDO = True


def verify_vagrant(state, host):
    command = 'vagrant --version'
    status, stdout, stderr = host.run_shell_command(state, command=command, sudo=SUDO)
    assert status is True  # ensure the command executed OK
    if 'Vagrant ' not in str(stdout):
        raise Exception('`{}` did not work as expected.stdout:{} stderr:{}'.format(
            command, stdout, stderr))


if host.get_fact(LinuxName) == 'Ubuntu':

    apt.packages(
        name='Install required packages',
        packages=['wget', 'unzip', 'python3'],
        update=True,
    )

    files.download(
        name='Download the Vagrantup Downloads page',
        src='https://www.vagrantup.com/downloads.html',
        dest='/tmp/downloads.html',
    )

    server.script_template(
        name='Use wget to download and unzip to /usr/local/bin',
        src='templates/download_vagrant.bash.j2',
    )

    python.call(
        name='Verify vagrant is installed by running version command',
        function=verify_vagrant,
    )
