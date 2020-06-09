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

    Examples:

    .. code:: python

        # Note: If using URL, wget is assumed to be installed.
        apt.key(
            {'Add the Docker apt gpg key'},
            key='https://download.docker.com/linux/ubuntu/gpg',
        )

        apt.key(
            {'Install VirtualBox key'},
            'https://www.virtualbox.org/download/oracle_vbox_2016.asc',
        )

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
    Add/remove apt repositories.

    + name: apt source string eg ``deb http://X hardy main``
    + present: whether the repo should exist on the system
    + filename: optional filename to use ``/etc/apt/sources.list.d/<filename>.list``. By
      default uses ``/etc/apt/sources.list``.

    Example:

    .. code:: python

        apt.repo(
            {'Install VirtualBox repo'},
            'deb https://download.virtualbox.org/virtualbox/debian bionic contrib',
        )

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
            state, host, filename, name,
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
    Add/remove Ubuntu ppa repositories.

    + name: the PPA name (full ppa:user/repo format)
    + present: whether it should exist

    Note:
        requires ``apt-add-repository`` on the remote host

    Example:

    .. code:: python

        # Note: Assumes software-properties-common is installed.
        apt.ppa(
            {'Add the Bitcoin ppa'},
            'ppa:bitcoin/bitcoin',
        )

    '''

    if present:
        yield 'apt-add-repository -y "{0}"'.format(name)

    if not present:
        yield 'apt-add-repository -y --remove "{0}"'.format(name)


@operation
def deb(state, host, source, present=True, force=False):
    '''
    Add/remove ``.deb`` file packages.

    + source: filename or URL of the ``.deb`` file
    + present: whether or not the package should exist on the system
    + force: whether to force the package install by passing `--force-yes` to apt

    Note:
        When installing, ``apt-get install -f`` will be run to install any unmet
        dependencies.

    URL sources with ``present=False``:
        If the ``.deb`` file isn't downloaded, pyinfra can't remove any existing
        package as the file won't exist until mid-deploy.

    Example:

    .. code:: python

        # Note: Assumes wget is installed.
        apt.deb(
            {'Install Chrome via deb'},
            'https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb',
        )
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
            and info.get('version') in current_packages[info['name']]
        ):
            exists = True

    # Package does not exist and we want?
    if present and not exists:
        # Install .deb file - ignoring failure (on unmet dependencies)
        yield 'dpkg --force-confdef --force-confold -i {0} 2> /dev/null || true'.format(source)
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
def update(state, host, cache_time=None, touch_periodic=False):
    '''
    Updates apt repositories.

    + cache_time: cache updates for this many seconds
    + touch_periodic: touch ``/var/lib/apt/periodic/update-success-stamp`` after update
    '''

    # If cache_time check when apt was last updated, prevent updates if within time
    if cache_time:
        # Ubuntu provides this handy file
        cache_info = host.fact.file(APT_UPDATE_FILENAME)

        # Time on files is not tz-aware, and will be the same tz as the server's time,
        # so we can safely remove the tzinfo from host.fact.date before comparison.
        host_cache_time = host.fact.date.replace(tzinfo=None) - timedelta(seconds=cache_time)
        if cache_info and cache_info['mtime'] and cache_info['mtime'] > host_cache_time:
            return

    yield 'apt-get update'

    # Some apt systems (Debian) have the /var/lib/apt/periodic directory, but
    # don't bother touching anything in there - so pyinfra does it, enabling
    # cache_time to work.
    if cache_time:
        yield 'touch {0}'.format(APT_UPDATE_FILENAME)

_update = update  # noqa: E305


@operation
def upgrade(state, host):
    '''
    Upgrades all apt packages.
    '''

    yield noninteractive_apt('upgrade')

_upgrade = upgrade  # noqa: E305 (for use below where update is a kwarg)


@operation
def packages(
    state, host,
    packages=None, present=True, latest=False,
    update=False, cache_time=None, upgrade=False,
    force=False, no_recommends=False,
    allow_downgrades=False,
):
    '''
    Install/remove/update packages & update apt.

    + packages: list of packages to ensure
    + present: whether the packages should be installed
    + latest: whether to upgrade packages without a specified version
    + update: run apt update before installing packages
    + cache_time: when used with update, cache for this many seconds
    + upgrade: run apt upgrade before installing packages
    + force: whether to force package installs by passing `--force-yes` to apt
    + no_recommends: don't install recommended packages
    + allow_downgrades: allow downgrading packages with version (--allow-downgrades)

    Versions:
        Package versions can be pinned like apt: ``<pkg>=<version>``

    Cache time:
        When ``cache_time`` is set the ``/var/lib/apt/periodic/update-success-stamp`` file
        is touched upon successful update. Some distros already do this (Ubuntu), but others
        simply leave the periodic directory empty (Debian).

    Examples:

    .. code:: python

        # Update package list and install packages
        apt.packages(
            {'Install Asterisk and Vim'},
            ['asterisk', 'vim'],
            update=True,
        )

        # Install the latest versions of packages (always check)
        apt.packages(
            {'Install latest Vim'},
            ['vim'],
            latest=True,
        )

        # Note: host.fact.os_version is the same as `uname -r` (ex: '4.15.0-72-generic')
        apt.packages(
            {'Install kernel headers'},
            ['linux-headers-{}'.format(host.fact.os_version)],
            update=True,
        )

    '''

    if update:
        yield _update(state, host, cache_time=cache_time)

    if upgrade:
        yield _upgrade(state, host)

    install_command = 'install'
    if no_recommends is True:
        install_command += ' --no-install-recommends'
    if allow_downgrades:
        install_command += ' --allow-downgrades'

    # Compare/ensure packages are present/not
    yield ensure_packages(
        packages, host.fact.deb_packages, present,
        install_command=noninteractive_apt(install_command, force=force),
        uninstall_command=noninteractive_apt('remove', force=force),
        upgrade_command=noninteractive_apt(install_command, force=force),
        version_join='=',
        latest=latest,
    )
