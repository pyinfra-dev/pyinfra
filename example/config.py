# pyinfra
# File: example/config
# Desc: example config script

#################### Required
# SSH details
SSH_HOSTS = [
    '20.20.20.21',
    '20.20.20.22',
    '20.20.20.23',
    '20.20.20.24',
    '20.20.20.25'
]
SSH_PORT = 22
SSH_USER = 'vagrant'
SSH_KEY = './insecure_private_key'


#################### Optional
# Sudo everything
SUDO = False
# & the user
SUDO_USER = 'root'

# Ignore errors
IGNORE_ERRORS = False

# a None/undefined is equivalent to 100, ignored when --serial/--nowait
FAIL_PERCENT = 20


#################### Whatever you want
ENV_DIR = '/opt/env'
APP_DIR = '/opt/pyinfra'
