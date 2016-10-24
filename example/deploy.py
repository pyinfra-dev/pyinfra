# pyinfra
# File: pyinfra/example/deploy.py
# Desc: example deploy script for the pyinfra CLI
#       targets: Ubuntu/Debian, CentOS/Fedora & OpenBSD

# Host represents the *current* server begin managed
from pyinfra import host, inventory, local, hook

# Modules provide namespaced operations, which do the work
from pyinfra.modules import server, apt, yum, files, python, git, pip, init


# Hooks inside deploy file
@hook.before_connect
def before_connect(data, state):
    print('inventory hosts!: ', [host.name for host in inventory])


# Ensure the state of a user
server.user(
    'pyinfra',
    shell='/bin/sh',
    ensure_home=True,

    # Options available for all operations
    sudo=True,
    sudo_user='root',
    ignore_errors=False,
    serial=False,
    run_once=False,
    get_pty=False,
    timeout=30  # only applies to commands on the remote host (not SFTP, local Python)
)

# And groups
server.group(
    {'Ensure pyinfra2 group exists'},  # use a set as the first arg to set the op name
    'pyinfra2',
    sudo=True,
    run_once=True  # run only on one host
)

# Ensure the state of files
files.file(
    '/var/log/pyinfra.log',
    user='pyinfra',
    group='pyinfra',
    mode=644,
    sudo=True
)

# Ensure the state of directories
files.directory(
    host.data.env_dir,
    user='pyinfra',
    group='pyinfra',
    mode=755,
    recursive=True,
    sudo=True,
    serial=True
)

# Copy local files to remote host
files.put(
    'files/file.txt',
    '/home/vagrant/file.txt',
    mode=777
)
# and sync directories
files.sync(
    'files',
    '/home/vagrant/example_files',
    user='pyinfra',
    group='pyinfra',
    delete=True,
    sudo=True
)

# Generate files from local jinja2 templates
files.template(
    'templates/template.txt.j2',
    '/home/vagrant/template.txt'
)

# Execute arbitrary shell commands
server.shell([
    'echo "Shell command"',
    'echo "My hostname is {{ host.fact.hostname }}"'
])
# and scripts
server.script(
    'files/test.sh'
)

# Manage init systems
init.d(
    'cron',
    running=True,
    sudo=True,
    ignore_errors=True
)

# Include roles
local.include(
    'roles/bsd_role.py',
    hosts=inventory.bsd  # optionally limit the role to a subset of hosts
)

# Storing this fact to avoid typing it so much (because the example targets a whole bunch
# of distros [& 2 OSs]).
distro = host.fact.linux_distribution

# Work with facts about the remote host
if distro['name'] in ('Debian', 'Ubuntu'):
    # apt package manager
    apt.packages(
        ['git', 'python-pip'],
        sudo=True,
        update=True,
        cache_time=3600
    )

elif distro['name'] in ('CentOS', 'Fedora'):
    if distro['name'] == 'CentOS':
        # Both missing in the CentOS 7 Vagrant image
        yum.packages(
            ['wget', 'net-tools'],
            sudo=True
        )

        # Manage remote rpm files
        yum.rpm(
            'https://dl.fedoraproject.org/pub/epel/epel-release-latest-{{ host.fact.linux_distribution.major }}.noarch.rpm',
            sudo=True
        )

    # yum package manager
    yum.packages(
        ['git', 'python-pip'],
        sudo=True
    )

    # Edit lines in files
    files.line(
        '/etc/sysconfig/selinux',
        '^SELINUX=.*',
        replace='SELINUX=disabled',
        sudo=True
    )

# Ensure the state of git repositories
git.repo(
    'https://github.com/Fizzadar/pyinfra',
    host.data.app_dir,
    branch='develop',
    sudo=True
    # Do the git clone/pull as the SSH user when using forwarding
    # use_ssh_user=True
)

# Manage pip (npm, gem) packages
did_install = pip.packages(
    ['virtualenv'],
    sudo=True
)
# use operation meta to affect the deploy
if did_install.changed:
    server.shell(
        'echo "Clean package build/etc"'
    )

# Create a virtualenv
server.shell(
    'virtualenv {{ host.data.env_dir }}',
    sudo=True,
    sudo_user='pyinfra'
)
# and manage pip within it
pip.packages(
    ['ElasticQuery', 'JsonTest'],
    virtualenv=host.data.env_dir,
    sudo=True,
    sudo_user='pyinfra'
)

# Wait for services
server.wait(
    port=22,
    timeout=5
)

# Execute Python locally, mid-deploy
def some_python(state, host, hostname, *args, **kwargs):
    print('connecting hostname: {0}, actual: {1}'.format(hostname, host.fact.hostname))
    local.shell('echo "local stuff!"')

python.execute(some_python, 'arg1', 'arg2', kwarg='hello world')
