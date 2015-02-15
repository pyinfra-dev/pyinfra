# pyinfra
# File: pyinfra/modules/apt.py
# Desc: manage apt packages & repositories

from pyinfra.api import operation, server


@operation
def repo(name, present=True):
    return []


@operation
def packages(packages, present=True, update=False, upgrade=False):
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
