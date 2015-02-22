# pyinfra
# File: pyinfra/modules/apt.py
# Desc: manage apt packages & repositories

from pyinfra import host
from pyinfra.api import operation


@operation
def repo(name, present=True):
    '''[Not implemented] Manage yum sources.'''
    pass


@operation
def packages(packages, present=True, upgrade=False):
    '''Manage yum packages & updates.'''
    packages = packages if isinstance(packages, list) else [packages]
    commands = []

    if upgrade:
        commands.append('yum update -y')

    current_packages = host.rpm_packages
    packages = [
        package for package in packages
        if package not in current_packages
    ]

    if packages:
        commands.append('yum install -y {}'.format(' '.join(packages)))

    return commands


@operation
def rpm(rpm_file, present=True):
    '''[Not implemented] Install/remove .rpm packages with rpm'''
    pass
