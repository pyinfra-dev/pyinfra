# pyinfra
# File: example/deploy.py
# Desc: example deploy script for the pyinfra CLI, targets: Ubuntu/Debian, CentOS & OpenBSD

# Host represents the *current* server begin managed
from pyinfra import host

# Modules provide namespaced operations, which do the work
from pyinfra.modules import server, apt, yum, files, python, git, pip, pkg, init


# Ensure the state of a user
server.user(
    'pyinfra',
    home='/home/pyinfra',
    shell='/bin/bash',

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
files.file(
    '/var/log/pyinfra.log',
    user='pyinfra',
    group='pyinfra',
    mode='644',
    sudo=True
)

# Ensure the state of directories
files.directory(
    host.data.env_dir,
    user='pyinfra',
    group='pyinfra',
    mode='755',
    recursive=True,
    sudo=True,
    serial=True
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
    # non-standard kwargs are passed to the template
    hostname=host.hostname,
    sudo=True
)

# Work with facts about the remote host
if host.os == 'Linux':
    if host.linux_distribution['name'] in ('Debian', 'Ubuntu'):
        # apt package manager
        apt.packages(
            ['git', 'python-pip'],
            sudo=True,
            update=True,
            op='core_packages' # this and below binds these three operations to run as one
        )

    elif host.linux_distribution['name'] == 'CentOS':
        # yum package manager
        yum.packages(
            ['git'],
            sudo=True,
            op='core_packages' # this and above/below binds these three operations to run as one
        )

        # yum doesn't, by default, have pip
        server.shell(
            'wget https://bootstrap.pypa.io/get-pip.py -O /tmp/get-pip.py',
            'python /tmp/get-pip.py',
            sudo=True
        )

# Work with inventory groups
elif 'bsd' in host.groups:
    # OpenBSD packages?
    pkg.packages(
        ['py-pip'],
        sudo=True,
        op='core_packages' # this and above binds these three operations to run as one
    )

    # add_pkg does not automatically do this
    server.shell(
        'ln -sf /usr/local/bin/pip-2.7 /usr/local/bin/pip',
        sudo=True
    )

# Execute arbitrary shell commands
server.shell(
    'echo "Shell command"',
    'echo "And another!"'
)
# and scripts
server.script(
    'files/test.sh'
)

# Manage init systems
init.service(
    'crond',
    running=True,
    sudo=True,
    ignore_errors=True
)

# Execute Python locally, mid-deploy
def some_python(hostname, host):
    print 'connecting hostname: {0}, actual: {1}'.format(hostname, host.hostname)

python.execute(some_python)

# Ensure the state of git repositories
git.repo(
    'git@github.com:Fizzadar/pyinfra.git',
    host.data.app_dir,
    update=True,
    branch='develop'
)

# Manage pip packages
pip.packages(
    ['virtualenv'],
    sudo=True
)

# Create a virtualenv
server.shell(
    'virtualenv {0}'.format(host.data.env_dir),
    sudo=True,
    sudo_user='pyinfra'
)
# and manage pip within it
pip.packages(
    ['ElasticQuery', 'JsonTest'],
    venv=host.data.env_dir,
    sudo=True,
    sudo_user='pyinfra'
)
