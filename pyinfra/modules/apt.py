# pyinfra
# File: pyinfra/modules/apt.py
# Desc: manage apt packages & repositories

from pyinfra.api import operation, operation_env, server


@operation
def repo(name, present=True):
    '''Manage apt sources.'''
    pass


@operation
@operation_env(DEBIAN_FRONTEND='noninteractive') # surpresses interactive prompts
def packages(packages, present=True, update=False, upgrade=False):
    '''Install/remove/upgrade packages & update apt.'''
    commands = []

    if update:
        commands.append('apt-get update')
    if upgrade:
        commands.append('apt-get upgrade')

    current_packages = server.fact('DebPackages')
    packages = [
        package for package in packages
        if package not in current_packages
    ]

    if packages:
        commands.append('apt-get install -y {}'.format(' '.join(packages)))

    return commands


@operation
def deb(deb_file, present=True):
    '''Install/remove .deb packages with dpkg'''
    pass
