'''
Manage yum packages and repositories. Note that yum package names are case-sensitive.
'''

from io import StringIO

from pyinfra.api import operation

from . import files
from .util.packaging import ensure_packages, ensure_rpm


@operation
def key(state, host, key):
    '''
    Add yum gpg keys with ``rpm``.

    + key: filename or URL

    Note:
        always returns one command, not state checking

    Example:

    .. code:: python

        yum.key(
            {'Add the Docker CentOS gpg key'},
            'https://download.docker.com/linux/{{ host.fact.lsb_release.id|lower }}/gpg',
        )
    '''

    yield 'rpm --import {0}'.format(key)


@operation
def repo(
    state, host, name, baseurl,
    present=True, description=None, enabled=True, gpgcheck=True, gpgkey=None,
):
    '''
    Add/remove/update yum repositories.

    + name: filename for the repo (in ``/etc/yum/repos.d/``)
    + baseurl: the baseurl of the repo
    + present: whether the ``.repo`` file should be present
    + description: optional verbose description
    + gpgcheck: whether set ``gpgcheck=1``
    + gpgkey: the URL to the gpg key for this repo

    Example:

    .. code:: python

        yum.repo(
            {'Add the Docker CentOS repo'},
            name='DockerCE',
            baseurl='https://download.docker.com/linux/centos/7/$basearch/stable',
        )
    '''

    # Description defaults to name
    description = description or name

    filename = '/etc/yum.repos.d/{0}.repo'.format(name)

    # If we don't want the repo, just remove any existing file
    if not present:
        yield files.file(state, host, filename, present=False)
        return

    # Build the repo file from string
    repo_lines = [
        '[{0}]'.format(name),
        'name={0}'.format(description),
        'baseurl={0}'.format(baseurl),
        'enabled={0}'.format(1 if enabled else 0),
        'gpgcheck={0}'.format(1 if gpgcheck else 0),
    ]

    if gpgkey:
        repo_lines.append('gpgkey={0}'.format(gpgkey))

    repo_lines.append('')
    repo = '\n'.join(repo_lines)
    repo = StringIO(repo)

    # Ensure this is the file on the server
    yield files.put(state, host, repo, filename)


@operation
def rpm(state, host, source, present=True):
    '''
    Add/remove ``.rpm`` file packages.

    + source: filename or URL of the ``.rpm`` package
    + present: whether ore not the package should exist on the system

    URL sources with ``present=False``:
        If the ``.rpm`` file isn't downloaded, pyinfra can't remove any existing
        package as the file won't exist until mid-deploy.

    Example:

    .. code:: python

        yum.rpm(
           {'Install EPEL rpm to enable EPEL repo'},
           'https://dl.fedoraproject.org/pub/epel/epel-release-latest-'
           '{{  host.fact.linux_distribution.major }}.noarch.rpm',
        )
    '''

    yield ensure_rpm(state, host, files, source, present, 'yum')


@operation
def update(state, host):
    '''
    Updates all yum packages.
    '''

    yield 'yum update -y'

_update = update  # noqa: E305 (for use below where update is a kwarg)


@operation
def packages(
    state, host, packages=None,
    present=True, latest=False, update=False, clean=False, nobest=False,
    extra_install_args='', extra_uninstall_args='',
):
    '''
    Install/remove/update yum packages & updates.

    + packages: list of packages to ensure
    + present: whether the packages should be installed
    + latest: whether to upgrade packages without a specified version
    + update: run yum update
    + clean: run yum clean
    + nobest: add the no best option to install
    + extra_install_args: additional arguments to the yum install command
    + extra_uninstall_args: additional arguments to the yum uninstall command

    Versions:
        Package versions can be pinned like yum: ``<pkg>-<version>``

    Examples:

    .. code:: python

        # Update package list and install packages
        yum.packages(
            {'Install Vim and Vim enhanced'},
            ['vim-enhanced', 'vim'],
            update=True,
        )

        # Install the latest versions of packages (always check)
        yum.packages(
            {'Install latest Vim'},
            ['vim'],
            latest=True,
        )
    '''

    if clean:
        yield 'yum clean all'

    if update:
        yield _update(state, host)

    nobest_option = ''
    if nobest:
        nobest_option = ' --nobest'

    if extra_install_args != '':
        extra_install_args = ' ' + extra_install_args

    if extra_uninstall_args != '':
        extra_uninstall_args = ' ' + extra_uninstall_args

    yield ensure_packages(
        packages, host.fact.rpm_packages, present,
        install_command='yum install -y' + nobest_option + extra_install_args,
        uninstall_command='yum remove -y' + extra_uninstall_args,
        upgrade_command='yum update -y',
        version_join='-',
        latest=latest,
    )
