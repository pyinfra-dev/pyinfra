# pyinfra
# File: example/deploy.py
# Desc: example deploy script for the pyinfra CLI, targets: Ubuntu/Debian, CentOS & OpenBSD

# Host represents the *current* server begin managed
from pyinfra import host

# Modules provide namespaced operations, which do the work
from pyinfra.modules import server, apt, yum, files, python, git, pip, pkg, init, local


# Ensure the state of a user
server.user(
    'pyinfra',
    home='/home/pyinfra',
    shell='/bin/bash',

    # Options available for all operations
    name='Ensure user pyinfra',
    sudo=True,
    sudo_user='root',
    ignore_errors=False,
    serial=False,
    run_once=False,
    timeout=30 # ignored for SFTP transfers
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

files.directory(
    host.data.app_dir,
    user='pyinfra',
    group='pyinfra',
    sudo=True
)

# Copy local files to remote host
files.put(
    'files/file.txt',
    '/home/vagrant/file.txt',
    mode='777'
)
# and sync directories
files.sync(
    'files',
    '/home/pyinfra/example_files',
    user='pyinfra',
    group='pyinfra',
    sudo=True
)

# Generate files from local jinja2 templates
files.template(
    'templates/template.txt.jn2',
    '/home/vagrant/template.txt',
    # non-standard kwargs are passed to the template
    hostname=host.hostname
)

# Work with facts about the remote host
if host.os == 'Linux':
    if host.linux_distribution['name'] in ('Debian', 'Ubuntu'):
        # apt package manager
        apt.packages(
            ['git', 'python-pip'],
            sudo=True,
            update=True,
            update_time=3600,
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
        if not host.file('/tmp/get-pip.py'):
            server.shell('wget https://bootstrap.pypa.io/get-pip.py -O /tmp/get-pip.py')

        server.shell(
            'python /tmp/get-pip.py',
            sudo=True
        )

# Work with inventory groups
elif 'bsd' in host.groups:
    # OpenBSD packages?
    pkg.packages(
        ['py-pip', 'git'],
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
def some_python(hostname, host, *args, **kwargs):
    print 'args: {0}, kwargs: {1}'.format(args, kwargs)
    print 'connecting hostname: {0}, actual: {1}'.format(hostname, host.hostname)

python.execute(some_python, 'arg1', 'arg2', kwarg='hello world')

# Ensure the state of git repositories
git.repo(
    'https://github.com/Fizzadar/pyinfra',
    host.data.app_dir,
    branch='develop',
    sudo=True,
    sudo_user='pyinfra'
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

# Run things locally
local.shell(
    'echo "I am local!"',
    run_once=True
)

# Wait for services
server.wait(
    port=22,
    timeout=5
)
