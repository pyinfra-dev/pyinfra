# pyinfra
# File: pyinfra/modules/apt.py
# Desc: manage apt packages & repositories

'''
Manage apt packages and repositories.
'''

from datetime import timedelta

from pyinfra.api import operation, OperationException


@operation
def repo(state, host, name, present=True):
    '''[Not complete] Manage apt sources.'''
    return ['apt-add-repository {0} -y'.format(name)]


@operation
def ppa(state, host, name, **kwargs):
    '''[Not complete] Shortcut for managing ppa apt sources.'''
    return repo('ppa:{}'.format(name), **kwargs)


@operation
def packages(state, host, packages=None, present=True, update=False, cache_time=None, upgrade=False):
    '''Install/remove/upgrade packages & update apt.'''

    if packages is None:
        packages = []

    if isinstance(packages, basestring):
        packages = [packages]

    # apt packages are case-insensitive
    packages = [package.lower() for package in packages]

    commands = []

    # If cache_time check when apt was last updated, prevent updates if within time
    if cache_time:
        cache_info = host.file('/var/cache/apt/pkgcache.bin')
        # Time on files is not tz-aware, and will be the same tz as the server's time,
        # so we can safely remove the tzinfo from host.date before comparison.
        cache_time = host.date.replace(tzinfo=None) - timedelta(seconds=cache_time)
        if cache_info and cache_info['mtime'] and cache_info['mtime'] > cache_time:
            update = False

    if update:
        commands.append('apt-get update')

    if upgrade:
        commands.append('DEBIAN_FRONTEND=noninteractive apt-get upgrade -y')

    current_packages = host.deb_packages or {}

    if current_packages is None:
        raise OperationException('apt is not installed')

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
