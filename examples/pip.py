from pyinfra import host
from pyinfra.operations import apk, apt, files, pip, yum

SUDO = True

if host.fact.linux_name in ['Alpine']:
    apk.packages(
        name='Install packages for python virtual environments',
        packages=[
            'gcc',
            'libffi-dev',
            'make',
            'musl-dev',
            'openssl-dev',
            'py3-pynacl',
            'py3-virtualenv',
            'python3-dev',
        ],
    )

if host.fact.linux_name in ['CentOS']:
    yum.packages(
        name='Install pip3 so you can install virtualenv',
        packages='python3-pip',
    )

if host.fact.linux_name in ['Ubuntu']:
    apt.packages(
        name='Install pip3 so you can install virtualenv',
        packages='python3-pip',
        update=True,
    )

if not host.fact.file('/usr/bin/pip'):
    files.link(
        name='Create link /usr/bin/pip that points to /usr/bin/pip3',
        path='/usr/bin/pip',
        target='/usr/bin/pip3',
    )

pip.packages(
    name='Install virtualenv using pip',
    packages='virtualenv',
)

pip.virtualenv(
    name='Create a virtualenv',
    path='/usr/local/bin/venv',
)

# use that virtualenv to install pyinfra
pip.packages(
    name='Install pyinfra into a virtualenv',
    packages='pyinfra',
    virtualenv='/usr/local/bin/venv',
)

# show that we can actually run the pyinfra command from that virtualenv
cmd = '/bin/bash -c "source /usr/local/bin/venv/bin/activate && pyinfra --version"'
stdout = host.fact.command(cmd)
print('\n\nstdout:', stdout, '\n\n')
