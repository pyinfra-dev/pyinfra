# pyinfra
# File: pyinfra/modules/yum.py
# Desc: manage yum packages & repositories

'''
Manage yum packages and repositories. Note that yum package names are case-sensitive.

Uses:

+ `yum`
'''

from pyinfra.api import operation, OperationError


@operation
def repo(state, host, name, present=True):
    '''[Not implemented] Manage yum repositories.'''
    pass


@operation
def packages(state, host, packages=None, present=True, upgrade=False, clean=False):
    '''Manage yum packages & updates.'''
    if packages is None:
        packages = []

    commands = []

    if clean:
        commands.append('yum clean all')

    if upgrade:
        commands.append('yum update -y')

    current_packages = host.rpm_packages or {}

    if current_packages is None:
        raise OperationError('yum is not installed')

    if present is True:
        # Packages specified but not installed
        diff_packages = [
            package for package in packages
            if package not in current_packages
        ]

        if diff_packages:
            commands.append('yum install -y {0}'.format(' '.join(diff_packages)))

    else:
        # Packages specified & installed
        diff_packages = [
            package for package in packages
            if package in current_packages
        ]

        if diff_packages:
            commands.append('yum remove -y {0}'.format(' '.join(diff_packages)))

    return commands
