# pyinfra
# File: example/config.py
# Desc: example config script

import requests


#################### Required
# SSH details
servers = requests.get('http://grandcentral.edtd.net/infrastructure/api/servers').json()
SSH_HOSTS = [server['hostname'] for server in servers]
SSH_PORT = 22
SSH_USER = 'ubuntu'
SSH_KEY = '/Users/nick/.ssh/root.pem'
SSH_KEY_PASS = None


#################### Optional (+ defaults)
# Run commands in parallel
PARALLEL = True
# Sudo everything
SUDO = False
# Ignore all errors
IGNORE_ERRORS = False


#################### Whatever you want
ENV_DIR = '/opt/env'
