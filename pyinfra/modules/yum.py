# pyinfra
# File: pyinfra/modules/yum.py
# Desc: manage yum packages & repositories

'''
Manage yum packages and repositories. Note that yum package names are case-sensitive.
'''

from __future__ import unicode_literals

from six import StringIO
from six.moves.urllib.parse import urlparse

from pyinfra.api import operation

from . import files
from .util.packaging import ensure_packages


@operation
def key(state, host, key):
    '''
    Add yum gpg keys with ``rpm``.

    + key: filename or URL

    Note:
        always returns one command, not state checking
    '''

    return ['rpm --import {0}'.format(key)]


@operation
def repo(
    state, host, name, baseurl,
    present=True, description=None, gpgcheck=True, enabled=True
):
    '''
    Manage yum repositories.

    + name: filename for the repo (in ``/etc/yum/repos.d/``)
    + baseurl: the baseurl of the repo
    + present: whether the ``.repo`` file should be present
    + description: optional verbose description
    + gpgcheck: whether set ``gpgcheck=1``
    '''

    # Description defaults to name
    description = description or name

    filename = '/etc/yum.repos.d/{0}.repo'.format(name)

    # If we don't want the repo, just remove any existing file
    if not present:
        return files.file(state, host, filename, present=False)

    # Build the repo file from string
    repo = '''
[{name}]
name={description}
baseurl={baseurl}
gpgcheck={gpgcheck}
enabled={enabled}
'''.format(
        name=name, baseurl=baseurl, description=description,
        gpgcheck=1 if gpgcheck else 0,
        enabled=1 if enabled else 0
    )

    repo = StringIO(repo)

    # Ensure this is the file on the server
    commands = files.put(state, host, repo, filename)

    return commands


@operation
def rpm(state, host, source, present=True):
    '''
    Install/manage ``.rpm`` file packages.

    + source: filenameo or URL of the ``.rpm`` package
    + present: whether ore not the package should exist on the system

    URL sources with ``present=False``:
        if the ``.rpm`` file isn't downloaded, pyinfra can't remove any existing package
        as the file won't exist until mid-deploy
    '''

    commands = []

    # If source is a url
    if urlparse(source).scheme:
        # Generate a temp filename (with .rpm extension to please yum)
        temp_filename = '{0}.rpm'.format(state.get_temp_filename(source))

        # Ensure it's downloaded
        commands.extend(files.download(state, host, source, temp_filename))

        # Override the source with the downloaded file
        source = temp_filename

    # Check for file .rpm information
    info = host.fact.rpm_package(source)
    exists = False

    # We have info!
    if info:
        current_packages = host.fact.rpm_packages

        if (
            info['name'] in current_packages
            and current_packages[info['name']] == info['version']
        ):
            exists = True

    # Package does not exist and we want?
    if present and not exists:
        commands.extend([
            'yum localinstall -y {0}'.format(source)
        ])

    # Package exists but we don't want?
    if exists and not present:
        commands.extend([
            'yum remove -y {0}'.format(info['name'])
        ])

    return commands


@operation
def upgrade(state, host):
    '''
    Upgrades all yum packages.
    '''

    return ['yum update -y']

_upgrade = upgrade


@operation
def packages(
    state, host, packages=None,
    present=True, latest=False, upgrade=False, clean=False
):
    '''
    Manage yum packages & updates.

    + packages: list of packages to ensure
    + present: whether the packages should be installed
    + latest: whether to upgrade packages without a specified version
    + upgrade: run yum upgrade
    + clean: run yum clean
    '''

    commands = []

    if clean:
        commands.append('yum clean all')

    if upgrade:
        commands.extend(_upgrade(state, host))

    commands.extend(ensure_packages(
        packages, host.fact.rpm_packages, present,
        install_command='yum install -y',
        uninstall_command='yum remove -y',
        upgrade_command='yum update -y',
        latest=latest
    ))

    return commands
