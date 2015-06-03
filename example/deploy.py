# pyinfra
# File: example/deploy
# Desc: example deploy script

# Config represents the config.py used in this deploy
# & host represents the *current* server begin managed
from pyinfra import config, host
# Modules provide namespaced operations, which do the work
from pyinfra.modules import server, apt, yum, files, python


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

# Will fail, but be ignored, on non-apt systems
apt.packages(
    sudo=True,
    update=True,
    ignore_errors=True
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
        sudo=True,
        op='core_packages' # this and above binds these two operations to run as one
    )

# Copy local files to remote host
files.put(
    'files/file.txt',
    '/home/vagrant/file.txt'
)

# Generate files from local jinja2 templates
files.template(
    'templates/template.txt.jn2',
    '/root/template.txt',
    sudo=True,
    **{
        'hello': 'world'
    }
)

# Execute arbitrary shell commands
server.shell(
    'echo "Shell command" && echo "Another!"'
)
# and scripts
server.script(
    'files/test.sh'
)

# Manage init.d services
server.init(
    'cron',
    # This ensures we generate only one operation for the two command variations above
    op='cron_restart',
    restarted=True,
    sudo=True,
    ignore_errors=True
)

# Execute Python locally, mid-deploy
def some_python(hostname, **kwargs):
    print 'connecting hostname: {0}, actual: {1}'.format(hostname, kwargs['actual_hostname'])

python.execute(
    some_python,
    # Host facts must be passed in
    actual_hostname=host.hostname,
    # This ensures we generate only one operation for 3 individual function calls
    op='some_python'
)

# # Ensure the state of git repositories
# git.repo(
#     'git@github.com:Fizzadar/pyinfra.git',
#     config.APP_DIR,
#     update=True,
#     branch='develop'
# )

# # Ensure the state of virtualenvs
# venv.env(
#     config.ENV_DIR
# )

# # Enter a virtualenv
# with venv.enter(config.ENV_DIR):
#     # and manage pip packages within
#     pip.packages(
#         requirements_file='/opt/pyinfra/requirements.pip'
#     )
