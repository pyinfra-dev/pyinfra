# pyinfra
# File: pyinfra/example/deploy.py
# Desc: example deploy script for the pyinfra CLI
#       targets: Ubuntu/Debian, CentOS/Fedora & OpenBSD

from pyinfra import local


# These work everywhere
local.include('basics.py')
local.include('packages.py')
local.include('callbacks.py')
local.include('python_app.py')

