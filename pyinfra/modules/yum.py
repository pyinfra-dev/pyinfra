# pyinfra
# File: pyinfra/modules/apt.py
# Desc: manage apt packages & repositories

from pyinfra import host
from pyinfra.api import operation


@operation
def repo(name, present=True):
    '''[Not implemented] Manage yum repositories.'''
    pass


@operation
def packages(packages=None, present=True, upgrade=False, clean=False):
    '''Manage yum packages & updates.'''
    if packages is None:
        packages = []
    elif isinstance(packages, basestring):
        packages = [packages]

    commands = []

    if clean:
        commands.append('yum clean all')

    if upgrade:
        commands.append('yum update -y')

    current_packages = host.rpm_packages

    if present is True:
        # Packages specified but not installed
        diff_packages = [
            package for package in packages
            if package not in current_packages
        ]

        if diff_packages:
            commands.append('yum install -y {}'.format(' '.join(diff_packages)))

    else:
        # Packages specified & installed
        diff_packages = [
            package for package in packages
            if package in current_packages
        ]

        if diff_packages:
            commands.append('yum remove -y {}'.format(' '.join(diff_packages)))

    return commands
