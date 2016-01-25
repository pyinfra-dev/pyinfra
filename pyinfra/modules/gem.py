# pyinfra
# File: pyinfra/modules/gem.py
# Desc: manage gem packages

'''
Mange gem packages.
'''

from pyinfra.api import operation


@operation
def packages(state, host, packages=None, present=True):
    '''
    Manage gem packages.

    + packages: list of packages to ensure
    + present: whether the packages should be installed
    '''

    if packages is None:
        packages = []

    if isinstance(packages, basestring):
        packages = [packages]

    commands = []

    # Don't fail if gem not found as not system package manager
    current_packages = host.gem_packages or {}

    if present is True:
        diff_packages = [
            package for package in packages
            if package not in current_packages
        ]

        if diff_packages:
            commands.append('gem install {0}'.format(' '.join(diff_packages)))

    else:
        diff_packages = [
            package for package in packages
            if package in current_packages
        ]

        if diff_packages:
            commands.append('gem uninstall {0}'.format(' '.join(diff_packages)))

    return commands
