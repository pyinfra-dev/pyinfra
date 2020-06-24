from __future__ import unicode_literals

from pyinfra.api import operation

from . import files
from .util.packaging import ensure_packages, ensure_rpm, ensure_zypper_repo
from .yum import key as yum_key

key = yum_key


@operation
def repo(
    state,
    host,
    name,
    baseurl=None,
    present=True,
    description=None,
    enabled=True,
    gpgcheck=True,
    gpgkey=None,
    type=None,
):
    '''
    Add/remove/update zypper repositories.

    + name: URL or name for the ``.repo``   file
    + baseurl: the baseurl of the repo (if ``name`` is not a URL)
    + present: whether the ``.repo`` file should be present
    + description: optional verbose description
    + enabled: whether this repo is enabled
    + gpgcheck: whether set ``gpgcheck=1``
    + gpgkey: the URL to the gpg key for this repo
    + type: the type field this repo (defaults to ``rpm-md``)

    ``Baseurl``/``description``/``gpgcheck``/``gpgkey``:
        These are only valid when ``name`` is a filename (ie not a URL). This is
        for manual construction of repository files. Use a URL to download and
        install remote repository files.

    Examples:

    .. code:: python

        # Download a repository file
        zypper.repo(
            {'Install container virtualization repo via URL'},
            'https://download.opensuse.org/repositories/Virtualization:containers/openSUSE_Tumbleweed/Virtualization:containers.repo',
        )

        # Create the repository file from baseurl/etc
        zypper.repo(
            {'Install container virtualization repo'},
            name='Virtualization:containers (openSUSE_Tumbleweed)',
            baseurl='https://download.opensuse.org/repositories/Virtualization:/containers/openSUSE_Tumbleweed/',
        )
    '''

    yield ensure_zypper_repo(
        state,
        host,
        files,
        name,
        baseurl,
        present,
        description,
        enabled,
        gpgcheck,
        gpgkey,
        type,
    )


@operation
def rpm(state, host, source, present=True):
    # NOTE: if updating this docstring also update `dnf.rpm`
    '''
    Add/remove ``.rpm`` file packages.

    + source: filename or URL of the ``.rpm`` package
    + present: whether ore not the package should exist on the system

    URL sources with ``present=False``:
        If the ``.rpm`` file isn't downloaded, pyinfra can't remove any existing
        package as the file won't exist until mid-deploy.

    Example:

    .. code:: python

        zypper.rpm(
           {'Install task from rpm'},
           'https://github.com/go-task/task/releases/download/v2.8.1/task_linux_amd64.rpm'
        )
    '''

    yield ensure_rpm(state, host, files, source, present, 'zypper --non-interactive')


@operation
def update(state, host):
    '''
    Updates all zypper packages.
    '''

    yield 'zypper update -y'


_update = update  # noqa: E305 (for use below where update is a kwarg)


@operation
def packages(
    state,
    host,
    packages=None,
    present=True,
    latest=False,
    update=False,
    clean=False,
    extra_global_install_args=None,
    extra_install_args=None,
    extra_global_uninstall_args=None,
    extra_uninstall_args=None,
):
    '''
    Install/remove/update zypper packages & updates.

    + packages: list of packages to ensure
    + present: whether the packages should be installed
    + latest: whether to upgrade packages without a specified version
    + update: run zypper update
    + clean: run zypper clean
    + extra_global_install_args: additional global arguments to the zypper install command
    + extra_install_args: additional arguments to the zypper install command
    + extra_global_uninstall_args: additional global arguments to the zypper uninstall command
    + extra_uninstall_args: additional arguments to the zypper uninstall command

    Versions:
        Package versions can be pinned like zypper: ``<pkg>=<version>``

    Examples:

    .. code:: python

        # Update package list and install packages
        zypper.packages(
            {'Install Vim and Vim enhanced'},
            ['vim-enhanced', 'vim'],
            update=True,
        )

        # Install the latest versions of packages (always check)
        zypper.packages(
            {'Install latest Vim'},
            ['vim'],
            latest=True,
        )
    '''

    if clean:
        yield 'zypper clean --all'

    if update:
        yield _update(state, host)

    install_command = ['zypper', '--non-interactive', 'install', '-y']

    if extra_install_args:
        install_command.append(extra_install_args)

    if extra_global_install_args:
        install_command.insert(1, extra_global_install_args)

    uninstall_command = ['zypper', '--non-interactive', 'remove', '-y']

    if extra_uninstall_args:
        uninstall_command.append(extra_uninstall_args)

    if extra_global_uninstall_args:
        uninstall_command.insert(1, extra_global_uninstall_args)

    upgrade_command = 'zypper update -y'

    yield ensure_packages(
        packages,
        host.fact.rpm_packages,
        present,
        install_command=' '.join(install_command),
        uninstall_command=' '.join(uninstall_command),
        upgrade_command=upgrade_command,
        version_join='=',
        latest=latest,
    )
