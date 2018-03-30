# pyinfra
# File: pyinfra/example/deploy.py
# Desc: example deploy script for the pyinfra CLI
#       targets: Ubuntu/Debian, CentOS/Fedora & OpenBSD

from pyinfra import local


# These work everywhere
local.include('deploy_basics.py')
local.include('deploy_packages.py')
local.include('deploy_callbacks.py')
local.include('deploy_python_app.py')
