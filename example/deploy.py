# pyinfra
# File: example/deploy.py
# Desc: example deploy script

from pyinfra import config
from pyinfra.modules import server, linux, apt, yum, files


# Ensure the state of a user
linux.user(
    'pyinfra',
    home='/home/pyinfra',
    shell='/bin/bash',
    public_keys=[
        'abc',
        'def'
    ],
    delete_keys=True,

    # Global options on all module functions (operations)
    sudo=True,
    sudo_user='root',
    name='Ensure user pyinfra',
    ignore_errors=False
)

# Ensure the state of files
linux.file(
    '/var/log/pyinfra.log',
    user='pyinfra',
    group='pyinfra',
    permissions='644',
    sudo=True
)

# Ensure the state of directories
linux.directory(
    config.ENV_DIR,
    user='pyinfra',
    group='pyinfra',
    permissions='755',
    recursive=True,
    sudo=True
)

# Work with multiple linux distributions
if server.fact('Distribution')['name'] == 'CentOS':
    # yum package manager
    yum.packages(
        ['python-devel', 'git'],
        sudo=True
    )
else:
    # apt package manager
    apt.packages(
        ['python-dev', 'git', 'nginx'],
        update=True,
        sudo=True
    )

# Copy local files to remote host
files.put(
    'filename.txt',
    '/home/ubuntu/filename.txt'
)

# Generate files from local jinja2 templates
files.template(
    'filename.jn2',
    '/opt/wheverever/test.sh',
    **{
        'hello': 'world'
    }
)

# Execute arbitrary shell commands
server.shell(
    'echo "hello"'
)
# # and scripts
# server.script('''
#     #!/bin/sh

#     echo "Shell script!"
#     exit 0
# ''')
# # and files
# server.script(
#     file='files/test.sh',
# )

# # Ensure the state of git repositories
# git.repo(
#     'git@github.com:Fizzadar/pyinfra.git',
#     config.APP_DIR,
#     update=True,
#     branch='develop'
# )

# # Ensure the state of virtualenvs
# venv.env(
#     config.ENV_DIR,
#     present=True
# )

# # Enter a virtualenv
# with venv.enter(config.ENV_DIR):
#     # Manage pip packages within
#     pip.packages(
#         requirements_file='/opt/pyinfra/requirements.pip',
#         present=True
#     )

# Manage init.d services
linux.init(
    'cron',
    restarted=True,
    ignore_errors=True
)
