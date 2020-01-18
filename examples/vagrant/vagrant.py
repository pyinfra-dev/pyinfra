from pyinfra import host
from pyinfra.modules import apt, files, python, server

SUDO = True


def verify_vagrant(state, host):
    command = 'vagrant --version'
    status, stdout, stderr = host.run_shell_command(state, command=command, sudo=SUDO)
    assert status is True  # ensure the command executed OK
    if 'Vagrant ' not in str(stdout):
        raise Exception('`{}` did not work as expected.stdout:{} stderr:{}'.format(
            command, stdout, stderr))


if host.fact.linux_name == 'Ubuntu':

    apt.packages(
        {'Install required packages'},
        ['wget', 'unzip', 'python3'],
        update=True,
    )

    files.download(
        {'Download the Vagrantup Downloads page'},
        'https://www.vagrantup.com/downloads.html',
        '/tmp/downloads.html',
    )

    # TODO: would like to be able to use files.download() but
    # I don't know how to download a file, look for a pattern, then
    # use that pattern in another files.download()
    server.script_template(
        {'Use wget to download and unzip to /usr/local/bin'},
        'templates/download_vagrant.bash.j2',
    )

    python.call(
        {'Verify vagrant is installed by running version command'},
        verify_vagrant,
    )
