# pyinfra
# File: pyinfra/modules/apt.py
# Desc: manage apt packages & repositories

from pyinfra.api import operation, server


@operation
def repo(name, present=True):
    pass


@operation
def packages(packages, present=True, upgrade=False):
    commands = []

    current_packages = server.fact('RPMPackages')
    packages = [
        package for package in packages
        if package not in current_packages
    ]

    if packages:
        commands.append('yum install -y {}'.format(' '.join(packages)))

    return commands
