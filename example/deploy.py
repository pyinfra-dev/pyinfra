# pyinfra
# File: example/deploy
# Desc: example deploy script

# Config represents the config.py used in this deploy
# & host represents the *current* server begin managed
from pyinfra import config, host
# Modules provide namespaced operations, which do the work
from pyinfra.modules import server, apt, yum, files


# Ensure the state of a user
server.user(
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
server.file(
    '/var/log/pyinfra.log',
    user='pyinfra',
    group='pyinfra',
    permissions='644',
    sudo=True
)

# Ensure the state of directories
server.directory(
    config.ENV_DIR,
    user='pyinfra',
    group='pyinfra',
    permissions='755',
    recursive=True,
    sudo=True
)

# Work with multiple linux distributions
if host.distribution['name'] == 'CentOS':
    # yum package manager
    yum.packages(
        ['python-devel', 'git'],
        upgrade=True,
        sudo=True,
        op='core_packages' # this and below binds these two operations to run as one
    )
else:
    # apt package manager
    apt.packages(
        ['python-dev', 'git', 'nginx', 'python-software-properties', 'software-properties-common'],
        update=True,
        upgrade=True,
        sudo=True,
        op='core_packages' # this and above binds these two operations to run as one
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
# linux.script('''
#     #!/bin/sh

#     echo "Shell script!"
#     exit 0
# ''')
# # and files
# linux.script(
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
if host.distribution['name'] == 'CentOS':
    server.init(
        'crond',
        op='cron_restart',
        restarted=True,
        ignore_errors=True
    )
else:
    server.init(
        'cron',
        op='cron_restart',
        restarted=True,
        ignore_errors=True
    )
