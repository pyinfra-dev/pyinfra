# pyinfra
# File: pyinfra/modules/apt.py
# Desc: manage apt packages & repositories

from pyinfra import host
from pyinfra.api import operation, operation_env


@operation
def repo(name, present=True):
    '''[Not complete] Manage apt sources.'''
    return ['apt-add-repository {} -y'.format(name)]

@operation
def ppa(name, **kwargs):
    '''[Not complete] Shortcut for managing ppa apt sources.'''
    return repo.__decorated__('ppa:{}'.format(name), **kwargs)


@operation
@operation_env(DEBIAN_FRONTEND='noninteractive') # surpresses interactive prompts
def packages(packages, present=True, update=False, upgrade=False):
    '''Install/remove/upgrade packages & update apt.'''
    packages = packages if isinstance(packages, list) else [packages]
    commands = []

    if update:
        commands.append('apt-get update')
    if upgrade:
        commands.append('apt-get upgrade -y')

    current_packages = host.deb_packages

    if present is True:
        # Packages specified but not installed
        diff_packages = ' '.join([
            package for package in packages
            if package not in current_packages
        ])
        commands.append('apt-get install -y {}'.format(diff_packages))
    else:
        # Packages specified & installed
        diff_packages = ' '.join([
            package for package in packages
            if package in current_packages
        ])
        commands.append('apt-get remove -y {}'.format(diff_packages))

    return commands


@operation
def deb(deb_file, present=True):
    '''[Not implemented] Install/remove .deb packages with dpkg'''
    pass
