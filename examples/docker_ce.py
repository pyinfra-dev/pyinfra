from pyinfra import host
from pyinfra.facts.server import LinuxName, LsbRelease
from pyinfra.operations import apt, init, python

# Standalone example to show how to install Docker CE using
# https://docs.docker.com/install/linux/docker-ce/ubuntu/

# This script just shows how some pieces might fit together.
# Please see https://github.com/Fizzadar/pyinfra-docker
# for a more complete pyinfra docker installation.

SUDO = True
# If the remote system requires a password for sudo, un-comment the line below:
# USE_SUDO_PASSWORD = True


def check_docker_works(state, host):
    command = 'docker run hello-world'
    status, stdout, stderr = host.run_shell_command(command=command, sudo=SUDO)
    if not status or 'Hello from Docker!' not in stdout:
        raise Exception('`{}` did not work as expected'.format(command))


if host.get_fact(LinuxName) == 'Ubuntu':

    apt.packages(
        name='Ensure old docker packages are not present',
        packages=[
            'docker',
            'docker-engine',
            'docker.io',
            'containerd runc',
        ],
        present=False,
    )

    apt.packages(
        name='Ensure Docker CE prerequisites are present',
        packages=[
            'apt-transport-https',
            'ca-certificates',
            'curl',
            'gnupg-agent',
            'software-properties-common',
        ],
        update=True,
    )

    apt.key(
        name='Add the Docker apt gpg key if we need to',
        src='https://download.docker.com/linux/ubuntu/gpg',
    )

    lsb_info = host.get_fact(LsbRelease)
    linux_id = lsb_info['id'].lower()
    code_name = lsb_info['codename']

    apt.repo(
        name='Add the Docker CE apt repo',
        src=(
            'deb [arch=amd64] https://download.docker.com/linux/'
            '{} {} stable'.format(linux_id, code_name)
        ),
        filename='docker-ce-stable',
    )

    apt.packages(
        name='Ensure Docker CE is installed',
        packages=[
            'docker-ce',
            'docker-ce-cli',
            'containerd.io',
        ],
        update=True,
    )

    init.service(
        name='Ensure docker service is running',
        service='docker',
        running=True,
        enabled=True,
    )

    python.call(check_docker_works)
