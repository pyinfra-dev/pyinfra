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
    sudo=True,
    public_keys=[
        'abc',
        'def'
    ],
    delete_keys=True
)

linux.user(
    'vagrant',
    present=True,
    home='/home/vagrant',
    shell='/bin/bash',
    sudo=True,
    public_keys=[
        'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDmecJwEqI89wKjS6dndQnTQtK6aSLiQ8X5VquTmuDTh2tCA8qelCQloQi8o8IyVYx9qTwf0Nfpa6z8+mKiSMqQ38APJebc7TkGBjkYurDHAuZNSyY1Wv7M4TiOja2v0YU+7lqeGiYCQhx0/NgxYndwrlA4wB84KwLZd/IYBORdhCNclk+WzOEpaXMtaASnkjxQRfIzAROCeqQpsUj/dXKiuUV/2csUeEGEuM9k43yE+r7LruGsj0LqXVW4/7zpu1tIaIZz6X5ilmcTRbNh6u4EOdU/b3G1Xl6R50VzHe6vzGW8l2QZiVOZwvvDoySm3zBYVO2cADkfBuhVgfHD1JbH nick@oxygem.com'
    ]
)

# Ensure the state of files
linux.file(
    '/var/log/pyinfra.log',
    present=True,
    user='pyinfra',
    group='pyinfra',
    permissions='644',
    sudo=True
)

# Ensure the state of directories
linux.directory(
    config.ENV_DIR,
    present=True,
    user='pyinfra',
    group='pyinfra',
    permissions='755',
    sudo=True,
    recursive=True
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
if server.fact('Distribution')['name'] == 'CentOS':
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

# Execute arbitrary shell commands
server.shell(
    'nginx || sudo nginx',
    ignore_errors=True
)
# and scripts
server.script('''
    #!/bin/sh

    echo "Shell script!"
    exit 0
''')
# and files
server.script(
    file='files/test.sh',
)

# Ensure the state of git repositories
git.repo(
    'git@github.com:Fizzadar/pyinfra.git',
    config.APP_DIR,
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
    'nginx',
    restarted=True
)
