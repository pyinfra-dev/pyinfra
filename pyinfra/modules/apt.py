# pyinfra
# File: pyinfra/modules/apt.py
# Desc: manage apt packages & repositories

'''
Manage apt packages and repositories.

Uses:

+ `apt-get`
+ `apt-add-repository`
'''

from datetime import timedelta

from pyinfra import host
from pyinfra.api import operation, operation_facts, OperationError


@operation
def repo(name, present=True):
    '''[Not complete] Manage apt sources.'''
    return ['apt-add-repository {0} -y'.format(name)]


@operation
def ppa(name, **kwargs):
    '''[Not complete] Shortcut for managing ppa apt sources.'''
    return repo('ppa:{}'.format(name), **kwargs)


@operation
@operation_facts('deb_packages')
def packages(packages=None, present=True, update=False, update_time=None, upgrade=False):
    '''Install/remove/upgrade packages & update apt.'''
    if packages is None:
        packages = []

    # apt packages are case-insensitive
    packages = [package.lower() for package in packages]

    commands = []

    # If update_time check when apt was last updated, prevent updates if within time
    if update_time:
        cache_info = host.file('/var/cache/apt/pkgcache.bin')
        # Time on files is not tz-aware, and will be the same tz as the server's time,
        # so we can safely remove the tzinfo from host.date before comparison.
        update_time = host.date.replace(tzinfo=None) - timedelta(seconds=update_time)
        if cache_info and cache_info['mtime'] and cache_info['mtime'] > update_time:
            update = False

    if update:
        commands.append('apt-get update')

    if upgrade:
        commands.append('DEBIAN_FRONTEND=noninteractive apt-get upgrade -y')

    current_packages = host.deb_packages or {}

    if current_packages is None:
        raise OperationError('apt is not installed')

    if present is True:
        # Packages specified but not installed
        diff_packages = [
            package for package in packages
            if package not in current_packages
        ]

        if diff_packages:
            commands.append(
                'DEBIAN_FRONTEND=noninteractive apt-get install -y {0}'.format(
                    ' '.join(diff_packages)
                )
            )

    else:
        # Packages specified & installed
        diff_packages = [
            package for package in packages
            if package in current_packages
        ]

        if diff_packages:
            commands.append(
                'DEBIAN_FRONTEND=noninteractive apt-get remove -y {0}'.format(
                    ' '.join(diff_packages)
                )
            )

    return commands
