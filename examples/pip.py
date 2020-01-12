from pyinfra import host
from pyinfra.modules import apt, files, pip

SUDO = True

apt.packages(
    {'Install pip3 so you can install virtualenv'},
    'python3-pip',
)

if not host.fact.file('/usr/bin/pip'):
    files.link(
        {'Create link /usr/bin/pip that points to /usr/bin/pip3'},
        '/usr/bin/pip',
        '/usr/bin/pip3',
    )

pip.packages(
    {'Install virtualenv using pip'},
    'virtualenv',
)

pip.virtualenv(
    {'Create a virtualenv'},
    '/usr/local/bin/venv',
)

# use that virtualenv to install pyinfra
pip.packages(
    {'Install pyinfra into a virtualenv'},
    'pyinfra',
    virtualenv='/usr/local/bin/venv',
)

# show that we can actually run the pyinfra command from that virtualenv
cmd = '/bin/bash -c "source /usr/local/bin/venv/bin/activate && pyinfra --version"'
stdout = host.fact.command(cmd)
print('\n\nstdout:', stdout, '\n\n')
