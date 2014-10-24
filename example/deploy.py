# pyinfra
# File: example/deploy.py
# Desc: example deploy script

from pyinfra import config
from pyinfra.modules import server, linux, apt, git, pip, venv, yum, files


# Ensure the state of a user
linux.user(
    'pyinfra',
    present=True,
    home='/home/pydepoy',
    shell='/bin/bash',
    sudo=True
)

# Ensure the state of files
linux.file(
    '/var/log/pyinfra.log',
    present=True,
    owner='pyinfra',
    group='pyinfra',
    permissions='644',
    sudo=True
)

# Ensure the state of directories
linux.directory(
    '/opt/env',
    present=True,
    owner='pyinfra',
    group='pyinfra',
    permissions='755',
    sudo=True
)

# Generate files from local templates
files.template(
    'filename.jn2',
    '/opt/wheverever/test.sh',
    **{
        'hello': 'world'
    }
)

# Copy local files to remote host
files.put(
    'filename.txt',
    '/home/ubuntu/filename.txt'
)

# Work with multiple linux distributions
if server.fact('Distribution') == 'CentOS':
    # yum package manager
    yum.repo(
        'name',
        present=True
    )
    yum.packages(
        ['package', 'another'],
        present=True
    )
else:
    # apt package manager
    apt.repo(
        'app:wkgkwegk',
        present=True
    )
    apt.packages(
        ['package', 'psvkshr'],
        present=True
    )

# Execute arbitrary shell
server.shell(
    'nginx || sudo nginx',
    ignore_errors=True
)

# Ensure the state of git repositories
git.repo(
    'git@github.com:Fizzadar/pyinfra.git',
    '/opt/pyinfra',
    update=True,
    branch='develop'
)

# Ensure the state of virtualenvs
venv.env(
    config.ENV_DIR,
    present=True
)

# Enter a virtualenv
with venv.enter(config.ENV_DIR):
    # Manage pip packages within
    pip.packages(
        requirements_file='/opt/pyinfra/requirements.pip',
        present=True
    )

# Manage Linux services
linux.service(
    ['nginx', 'redis', 'rabbitmq'],
    restarted=True
)
