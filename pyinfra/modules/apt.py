# pyinfra
# File: pyinfra/modules/apt.py
# Desc: manage apt packages & repositories

'''
Manage apt packages and repositories.
'''

from datetime import timedelta

from pyinfra.api import operation, OperationException
from pyinfra.facts.apt import parse_apt_repo

from . import files


# TODO
#@operation
def deb(state, host, source, present=True):
    # If source is a url, get filename & ensure we have file
    # Check for file .deb information (if file is present)
    # Check if installed
    pass


@operation
def repo(state, host, name, present=True):
    '''
    Manage apt source repositories. Options:

    + name: apt line, repo url or PPA
    + present: whether the repo should exist on the system
    '''

    commands = []

    apt_sources = host.apt_sources or {}

    # Parse out the URL from the name if available
    repo = parse_apt_repo(name)
    if repo:
        name, _ = repo

    # Convert ppa's to full URLs
    elif name.startswith('ppa:'):
        name = 'http://ppa.launchpad.net/{0}/ubuntu'.format(name[4:])

    is_present = name in apt_sources

    # Doesn't exit and we want it
    if not is_present and present:
        commands.append('apt-add-repository {0} -y'.format(name))

    # Exists and we don't want it
    if is_present and not present:
        commands.append('apt-add-repository {0} -y --remove'.format(name))

    return commands


@operation
def packages(
    state, host,
    packages=None, present=True, update=False, cache_time=None, upgrade=False
):
    '''
    Install/remove/upgrade packages & update apt.

    + packages: list of packages to ensure
    + present: whether the packages should be installed
    + update: run apt update
    + cache_time: when used with update, cache for this many seconds
    + upgrade: run apt upgrade

    Note:
        ``cache_time`` only works on systems that provide the
        ``/var/lib/apt/periodic/update-success-stamp`` file (ie Ubuntu).
    '''

    if packages is None:
        packages = []

    if isinstance(packages, basestring):
        packages = [packages]

    # apt packages are case-insensitive
    packages = [package.lower() for package in packages]

    commands = []

    # If cache_time check when apt was last updated, prevent updates if within time
    if cache_time:
        # Ubuntu provides this handy file
        cache_info = host.file('/var/lib/apt/periodic/update-success-stamp')

        # Time on files is not tz-aware, and will be the same tz as the server's time,
        # so we can safely remove the tzinfo from host.date before comparison.
        cache_time = host.date.replace(tzinfo=None) - timedelta(seconds=cache_time)
        if cache_info and cache_info['mtime'] and cache_info['mtime'] > cache_time:
            update = False

    if update:
        commands.append('apt-get update')

    if upgrade:
        commands.append('DEBIAN_FRONTEND=noninteractive apt-get upgrade -y')

    current_packages = host.deb_packages

    # Raise error if apt isn't installed as it's a system package manager
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
