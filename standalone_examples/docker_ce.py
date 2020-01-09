from pyinfra import host
from pyinfra.modules import apt, server, python, init

# Standalone example to show how to install Docker CE using
# https://docs.docker.com/install/linux/docker-ce/ubuntu/

SUDO = True

if host.fact.linux_name == 'Ubuntu':

    apt.packages(
        {'Ensure old docker packages are not present'},
        [
            'docker',
            'docker-engine',
            'docker.io',
            'containerd runc',
        ],
        present=False,
    )

    apt.packages(
        {'Ensure Docker CE prerequisites are present'},
        [
            'apt-transport-https',
            'ca-certificates',
            'curl', 
            'gnupg-agent',
            'software-properties-common',
        ],
        update=True,
    )

    docker_key_exists = False
    stdout = host.fact.command('apt-key list')
    if 'Docker' in stdout:
        docker_key_exists = True

    if not docker_key_exists:
        apt.key(
            {'Add the Docker apt gpg key if we need to'},
            key='https://download.docker.com/linux/ubuntu/gpg',
        )

    apt.repo(
        {'Add the Docker CE apt repo'},
        (
            'deb [arch=amd64] https://download.docker.com/linux/'
            '{{ host.fact.lsb_release.id|lower }} '
            '{{ host.fact.lsb_release.codename }} stable'
        ),
        filename='docker-ce-stable',
    )

    apt.packages(
        {'Ensure Docker CE is installed'},
        [
            'docker-ce',
            'docker-ce-cli',
            'containerd.io',
        ],
        update=True,
    )

    init.service(
        {'Ensure docker service is running'},
        'docker',
        running=True,
        enabled=True,
    )

    # TODO: is NotImplementedEror the right value?
    # TODO: show the stdout if there is an error
    # TODO: when you change the docker to dockerf (to make it not found),
    #       the output is not in sequence; is that output or does it really
    #       not run these sequentially?
    stdout = host.fact.command('docker run hello-world')
    if stdout == None or 'Hello from Docker!' not in stdout:
        python.raise_exception(
            {'Post docker validation'},
            NotImplementedError,
            '`docker run hello-world` did not work as expected',
        )
