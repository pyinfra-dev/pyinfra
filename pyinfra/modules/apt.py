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

APT_UPDATE_FILENAME = '/var/lib/apt/periodic/update-success-stamp'


def noninteractive_apt(command, force=False):
    args = ['DEBIAN_FRONTEND=noninteractive apt-get -y']

    if force:
        args.append('--force-yes')

    args.extend((
        '-o Dpkg::Options::="--force-confdef"',
        '-o Dpkg::Options::="--force-confold"',
        command,
    ))

    return ' '.join(args)


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

    if key:
        # If URL, wget the key to stdout and pipe into apt-key, because the "adv"
        # apt-key passes to gpg which doesn't always support https!
        if urlparse(key).scheme:
            yield 'wget -O- {0} | apt-key add -'.format(key)
        else:
            yield 'apt-key add {0}'.format(key)

    if keyserver and keyid:
        yield 'apt-key adv --keyserver {0} --recv-keys {1}'.format(keyserver, keyid)


@operation
def repo(state, host, name, present=True, filename=None):
    '''
    Manage apt repositories.

    + name: apt source string eg ``deb http://X hardy main``
    + present: whether the repo should exist on the system
    + filename: optional filename to use ``/etc/apt/sources.list.d/<filename>.list``. By
      default uses ``/etc/apt/sources.list``.
    '''

    # Get the target .list file to manage
    if filename:
        filename = '/etc/apt/sources.list.d/{0}.list'.format(filename)
    else:
        filename = '/etc/apt/sources.list'

    # Work out if the repo exists already
    apt_sources = host.fact.apt_sources

    is_present = False
    repo = parse_apt_repo(name)
    if repo and repo in apt_sources:
        is_present = True

    # Doesn't exist and we want it
    if not is_present and present:
        yield files.line(
            state, host, filename, name
        )

    # Exists and we don't want it
    if is_present and not present:
        yield files.line(
            state, host, filename, name,
            present=False,
        )


@operation
def ppa(state, host, name, present=True):
    '''
    Manage Ubuntu ppa repositories.

    + name: the PPA name (full ppa:user/repo format)
    + present: whether it should exist

    Note:
        requires ``apt-add-repository`` on the remote host
    '''

    if present:
        yield 'apt-add-repository -y "{0}"'.format(name)

    if not present:
        yield 'apt-add-repository -y --remove "{0}"'.format(name)


@operation
def deb(state, host, source, present=True, force=False):
    '''
    Install/manage ``.deb`` file packages.

    + source: filename or URL of the ``.deb`` file
    + present: whether or not the package should exist on the system
    + force: whether to force the package install by passing `--force-yes` to apt

    Note:
        When installing, ``apt-get install -f`` will be run to install any unmet
        dependencies.

    URL sources with ``present=False``:
        If the ``.deb`` file isn't downloaded, pyinfra can't remove any existing
        package as the file won't exist until mid-deploy.
    '''

    # If source is a url
    if urlparse(source).scheme:
        # Generate a temp filename
        temp_filename = state.get_temp_filename(source)

        # Ensure it's downloaded
        yield files.download(state, host, source, temp_filename)

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
            and info['version'] in current_packages[info['name']]
        ):
            exists = True

    # Package does not exist and we want?
    if present and not exists:
        # Install .deb file - ignoring failure (on unmet dependencies)
        yield 'dpkg --force-confdef --force-confold -i {0} || true'.format(source)
        # Attempt to install any missing dependencies
        yield '{0} -f'.format(noninteractive_apt('install', force=force))
        # Now reinstall, and critically configure, the package - if there are still
        # missing deps, now we error
        yield 'dpkg --force-confdef --force-confold -i {0}'.format(source)

    # Package exists but we don't want?
    if exists and not present:
        yield '{0} {1}'.format(
            noninteractive_apt('remove', force=force),
            info['name'],
        )


@operation
def update(state, host, touch_periodic=False):
    '''
    Updates apt repos.

    + touch_periodic: touch ``/var/lib/apt/periodic/update-success-stamp`` after update
    '''

    yield 'apt-get update'

    # Some apt systems (Debian) have the /var/lib/apt/periodic directory, but
    # don't bother touching anything in there - so pyinfra does it, enabling
    # cache_time to work.
    if touch_periodic:
        yield 'touch {0}'.format(APT_UPDATE_FILENAME)

_update = update  # noqa


@operation
def upgrade(state, host):
    '''
    Upgrades all apt packages.
    '''

    yield noninteractive_apt('upgrade')

_upgrade = upgrade  # noqa


@operation
def packages(
    state, host,
    packages=None, present=True, latest=False,
    update=False, cache_time=None, upgrade=False,
    force=False, no_recommends=False,
):
    '''
    Install/remove/upgrade packages & update apt.

    + packages: list of packages to ensure
    + present: whether the packages should be installed
    + latest: whether to upgrade packages without a specified version
    + update: run apt update
    + cache_time: when used with update, cache for this many seconds
    + upgrade: run apt upgrade
    + force: whether to force package installs by passing `--force-yes` to apt
    + no_recommends: don't install recommended packages

    Versions:
        Package versions can be pinned like apt: ``<pkg>=<version>``

    Cache time:
        When ``cache_time`` is set the ``/var/lib/apt/periodic/update-success-stamp`` file
        is touched upon successful update. Some distros already do this (Ubuntu), but others
        simply leave the periodic directory empty (Debian).
    '''

    # If cache_time check when apt was last updated, prevent updates if within time
    if update and cache_time:
        # Ubuntu provides this handy file
        cache_info = host.fact.file(APT_UPDATE_FILENAME)

        # Time on files is not tz-aware, and will be the same tz as the server's time,
        # so we can safely remove the tzinfo from host.fact.date before comparison.
        host_cache_time = host.fact.date.replace(tzinfo=None) - timedelta(seconds=cache_time)
        if cache_info and cache_info['mtime'] and cache_info['mtime'] > host_cache_time:
            update = False

    if update:
        yield _update(state, host, touch_periodic=cache_time)

    if upgrade:
        yield _upgrade(state, host)

    install_command = (
        'install --no-install-recommends'
        if no_recommends is True
        else 'install'
    )

    # Compare/ensure packages are present/not
    yield ensure_packages(
        packages, host.fact.deb_packages, present,
        install_command=noninteractive_apt(install_command, force=force),
        uninstall_command=noninteractive_apt('remove', force=force),
        upgrade_command=noninteractive_apt(install_command, force=force),
        version_join='=',
        latest=latest,
    )
