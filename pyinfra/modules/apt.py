# pyinfra
# File: pyinfra/modules/apt.py
# Desc: manage apt packages & repositories

'''
Manage apt packages and repositories.
'''

from __future__ import unicode_literals

from datetime import timedelta

from six.moves.urllib.parse import urlparse

from pyinfra.api import operation
from pyinfra.facts.apt import parse_apt_repo

from . import files
from .util.packaging import ensure_packages


def noninteractive_apt(command):
    return ' '.join((
        'DEBIAN_FRONTEND=noninteractive apt-get -y',
        '-o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold"',
        command
    ))


@operation
def key(state, host, key=None, keyserver=None, keyid=None):
    '''
    Add apt gpg keys with ``apt-key``.

    + key: filename or URL
    + keyserver: URL of keyserver to fetch key from
    + keyid: key identifier when using keyserver

    Note:
        Always returns an add command, not state checking.

    keyserver/id:
        These must be provided together.
    '''

    commands = []

    if key:
        if urlparse(key).scheme:
            commands.append('apt-key adv --fetch-keys {0}'.format(key))
        else:
            commands.append('apt-key add {0}'.format(key))

    if keyserver and keyid:
        commands.append(
            'apt-key adv --keyserver {0} --recv-keys {1}'.format(keyserver, keyid)
        )

    return commands


@operation
def repo(state, host, name, present=True, filename=None):
    '''
    Manage apt repositories.

    + name: apt source string eg ``deb http://X hardy main``
    + present: whether the repo should exist on the system
    + filename: optional filename to use ``/etc/apt/sources.list.d/<filename>.list``. By
      default uses ``/etc/apt/sources.list``.
    '''

    commands = []

    apt_sources = host.fact.apt_sources

    # Get the target .list file to manage
    if filename:
        filename = '/etc/apt/sources.list.d/{0}.list'.format(filename)
    else:
        filename = '/etc/apt/sources.list'

    # Parse out the URL from the name if available
    repo_url = name
    repo = parse_apt_repo(name)
    if repo:
        repo_url, _ = repo

    is_present = repo_url in apt_sources

    # Doesn't exist and we want it
    if not is_present and present:
        commands.extend(files.line(
            state, host, filename, name
        ))

    # Exists and we don't want it
    if is_present and not present:
        commands.extend(files.line(
            state, host, filename, name, present=False
        ))

    return commands


@operation
def ppa(state, host, name, present=True):
    '''
    Manage Ubuntu ppa repositories.

    + name: the PPA name
    + present: whether it should exist

    Note:
        requires ``apt-add-repository`` on the remote host
    '''

    commands = []
    apt_sources = host.fact.apt_sources

    repo_url = 'http://ppa.launchpad.net/{0}/ubuntu'.format(name[4:])

    is_present = repo_url in apt_sources

    if not is_present and present:
        commands.append('apt-add-repository -y "{0}"'.format(name))

    if is_present and not present:
        commands.append('apt-add-repository -y --remove "{0}"'.format(name))

    return commands


@operation
def deb(state, host, source, present=True):
    '''
    Install/manage ``.deb`` file packages.

    + source: filename or URL of the ``.deb`` file
    + present: whether or not the package should exist on the system

    Note:
        when installing, ``apt-get install -f`` will be run to install any unmet
        dependencies

    URL sources with ``present=False``:
        if the ``.deb`` file isn't downloaded, pyinfra can't remove any existing package
        as the file won't exist until mid-deploy
    '''

    commands = []

    # If source is a url
    if urlparse(source).scheme:
        # Generate a temp filename
        temp_filename = state.get_temp_filename(source)

        # Ensure it's downloaded
        commands.extend(files.download(state, host, source, temp_filename))

        # Override the source with the downloaded file
        source = temp_filename

    # Check for file .deb information (if file is present)
    info = host.fact.deb_package(source)

    exists = False

    # We have deb info! Check against installed packages
    if info:
        current_packages = host.fact.deb_packages

        if (
            info['name'] in current_packages
            and current_packages[info['name']] == info['version']
        ):
            exists = True

    # Package does not exist and we want?
    if present and not exists:
        commands.extend([
            # Install .deb file - ignoring failure (on unmet dependencies)
            'dpkg --force-confdef --force-confold -i {0} || true'.format(source),
            # Attempt to install any missing dependencies
            '{0} -f'.format(noninteractive_apt('install')),
            # Now reinstall, and critically configure, the package - if there are still
            # missing deps, now we error
            'dpkg --force-confdef --force-confold -i {0}'.format(source)
        ])

    # Package exists but we don't want?
    if exists and not present:
        commands.extend([
            '{0} {1}'.format(noninteractive_apt('remove'), info['name'])
        ])

    return commands


@operation
def update(state, host):
    '''
    Updates apt repos.
    '''

    return ['apt-get update']

_update = update


@operation
def upgrade(state, host):
    '''
    Upgrades all apt packages.
    '''

    return [noninteractive_apt('upgrade')]

_upgrade = upgrade


@operation
def packages(
    state, host,
    packages=None, present=True, latest=False,
    update=False, cache_time=None, upgrade=False
):
    '''
    Install/remove/upgrade packages & update apt.

    + packages: list of packages to ensure
    + present: whether the packages should be installed
    + latest: whether to upgrade packages without a specified version
    + update: run apt update
    + cache_time: when used with update, cache for this many seconds
    + upgrade: run apt upgrade

    Versions:
        Package versions can be pinned like apt: ``<pkg>=<version>``

    Note:
        ``cache_time`` only works on systems that provide the
        ``/var/lib/apt/periodic/update-success-stamp`` file (ie Ubuntu).
    '''

    commands = []

    # If cache_time check when apt was last updated, prevent updates if within time
    if update and cache_time:
        # Ubuntu provides this handy file
        cache_info = host.fact.file('/var/lib/apt/periodic/update-success-stamp')

        # Time on files is not tz-aware, and will be the same tz as the server's time,
        # so we can safely remove the tzinfo from host.fact.date before comparison.
        cache_time = host.fact.date.replace(tzinfo=None) - timedelta(seconds=cache_time)
        if cache_info and cache_info['mtime'] and cache_info['mtime'] > cache_time:
            update = False

    if update:
        commands.extend(_update(state, host))

    if upgrade:
        commands.extend(_upgrade(state, host))

    # Compare/ensure packages are present/not
    commands.extend(ensure_packages(
        packages, host.fact.deb_packages, present,
        install_command=noninteractive_apt('install'),
        uninstall_command=noninteractive_apt('remove'),
        version_join='=',
        upgrade_command=noninteractive_apt('install'),
        latest=latest
    ))

    return commands
