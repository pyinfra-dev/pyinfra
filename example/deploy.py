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
    # these can be configured in config.py scripts
    sudo=True,
    sudo_user='root',
    ignore_errors=False,

    # Local options for all module functions
    name='Ensure user pyinfra',
    serial=False,
    run_once=False
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
    sudo=True,
    serial=True
)

# Work with multiple linux distributions
if host.distribution['name'] == 'CentOS':
    # yum package manager
    yum.packages(
        ['git'],
        clean=True,
        sudo=True,
        op='core_packages' # this and below binds these two operations to run as one
    )
else:
    # apt package manager
    apt.packages(
        ['git'],
        update=True,
        sudo=True,
        op='core_packages' # this and above binds these two operations to run as one
    )

# Will fail, but be ignored, on non-apt systems
apt.packages(
    'git',
    sudo=True,
    ignore_errors=True
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
    'echo "Shell command" && echo "Another!"'
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
#     # and manage pip packages within
#     pip.packages(
#         requirements_file='/opt/pyinfra/requirements.pip',
#         present=True
#     )

# Manage init.d services
server.init(
    'crond' if host.distribution['name'] == 'CentOS' else 'cron',
    op='cron_restart',
    restarted=True,
    ignore_errors=True
)
