from pyinfra import host
from pyinfra.operations import git, pip, server

# Ensure the state of git repositories
git.repo(
    name="Clone pyinfra repository",
    src="git@github.com:Fizzadar/pyinfra",
    dest=host.data.app_dir,
    branch="develop",
    ssh_keyscan=True,
    sudo=True,
    # Carry SSH agent details w/sudo
    preserve_sudo_env=True,
)

# Manage pip packages
did_install = pip.packages(
    name="Install virtualenv with pip",
    packages=["virtualenv"],
    sudo=True,
)
# Use operation meta to affect the deploy
if did_install.changed:
    server.shell(
        'echo "Clean package build/etc"',
    )

# Create a virtualenv
server.shell(
    name="Setup the virtualenv",
    commands="virtualenv {{ host.data.env_dir }}",
    sudo=True,
    sudo_user="pyinfra",
)
# and manage pip within it
pip.packages(
    name="Install Python packages with pip",
    packages=["ElasticQuery", "JsonTest"],
    virtualenv=host.data.env_dir,
    sudo=True,
    sudo_user="pyinfra",
)
