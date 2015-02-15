# pyinfra
# File: example/config.py
# Desc: example config script

#################### Required
# SSH details
SSH_HOSTS = [
    '20.20.20.20',
    '20.20.20.21',
    '20.20.20.22'
]
SSH_PORT = 22
SSH_USER = 'vagrant'
SSH_KEY = './files/insecure_private_key'


#################### Optional (+ defaults)
# Run commands in parallel
PARALLEL = True
# Sudo everything
SUDO = False
# Ignore all errors
IGNORE_ERRORS = False


#################### Whatever you want
ENV_DIR = '/opt/env'
APP_DIR = '/opt/pyinfra'
