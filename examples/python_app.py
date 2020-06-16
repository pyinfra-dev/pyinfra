from pyinfra import host
from pyinfra.modules import git, pip, server

# Ensure the state of git repositories
git.repo(
    {'Clone pyinfra repository'},
    'git@github.com:Fizzadar/pyinfra',
    host.data.app_dir,
    branch='develop',
    ssh_keyscan=True,
    sudo=True,
    # Carry SSH agent details w/sudo
    preserve_sudo_env=True,
)

# Manage pip packages
did_install = pip.packages(
    {'Install virtualenv with pip'},
    ['virtualenv'],
    sudo=True,
)
# Use operation meta to affect the deploy
if did_install.changed:
    server.shell(
        'echo "Clean package build/etc"',
    )

# Create a virtualenv
server.shell(
    {'Setup the virtualenv'},
    'virtualenv {{ host.data.env_dir }}',
    sudo=True,
    sudo_user='pyinfra',
)
# and manage pip within it
pip.packages(
    {'Install Python packages with pip'},
    ['ElasticQuery', 'JsonTest'],
    virtualenv=host.data.env_dir,
    sudo=True,
    sudo_user='pyinfra',
)
