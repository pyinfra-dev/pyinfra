from pyinfra import host
from pyinfra.modules import files, server


# Executing as the SSH user (vagrant):
#

# Generate files from local jinja2 templates
files.template(
    {'Generate/upload templates/template.txt.j2'},
    'templates/template.txt.j2',
    '/home/vagrant/template.txt',
)

server.shell(
    {'Execute some shell commands'},
    [
        'echo "Shell command"',
        'echo "My hostname is {{ host.fact.hostname }}"',
    ],
)
# and scripts
server.script(
    {'Run the files/test.sh script'},
    'files/test.sh',
)

# Copy local files to remote host
files.put(
    {'Upload files/file.txt'},
    'files/file.txt',
    '/home/vagrant/file.txt',
    mode=777,
)
# and sync directories
files.sync(
    {'Sync the files directory'},
    'files',
    '/home/vagrant/example_files',
    delete=True,
)


# Executing with sudo
#

# Ensure the state of a user
server.user(
    {'Ensure pyinfra user exists'},
    'pyinfra',
    shell='/bin/sh',

    # Global arguments available in all operations, for the full list see:
    # https://pyinfra.readthedocs.io/page/deploys.html#global-arguments
    sudo=True,
)

# And groups
server.group(
    {'Ensure pyinfra2 group exists'},  # use a set as the first arg to set the op name
    'pyinfra2',
    sudo=True,
)

# Ensure the state of files
files.file(
    {'Ensure pyinfra.log exists'},
    '/var/log/pyinfra.log',
    user='pyinfra',
    group='pyinfra',
    mode=644,
    sudo=True,
)

# Ensure the state of directories
files.directory(
    {'Ensure {{ host.data.env_dir }} exists exists'},
    host.data.env_dir,
    user='pyinfra',
    group='pyinfra',
    mode=755,
    sudo=True,
)
