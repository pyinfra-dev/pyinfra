'''
Manage apk packages.
'''

from pyinfra.api import operation

from .util.packaging import ensure_packages


@operation
def upgrade(state, host):
    '''
    Upgrades all apk packages.
    '''

    yield 'apk upgrade'

_upgrade = upgrade  # noqa: E305


@operation
def update(state, host):
    '''
    Updates apk repositories.
    '''

    yield 'apk update'

_update = update  # noqa: E305


@operation
def packages(
    state, host,
    packages=None, present=True, latest=False,
    update=False, upgrade=False,
):
    '''
    Add/remove/update apk packages.

    + packages: list of packages to ensure
    + present: whether the packages should be installed
    + latest: whether to upgrade packages without a specified version
    + update: run apk update before installing packages
    + upgrade: run apk upgrade before installing packages

    Versions:
        Package versions can be pinned like apk: ``<pkg>=<version>``.

    Examples:

    .. code:: python

        # Update package list and install packages
        apk.packages(
            {'Install Asterisk and Vim'},
            ['asterisk', 'vim'],
            update=True,
        )

        # Install the latest versions of packages (always check)
        apk.packages(
            {'Install latest Vim'},
            ['vim'],
            latest=True,
        )
    '''

    if update:
        yield _update(state, host)

    if upgrade:
        yield _upgrade(state, host)

    yield ensure_packages(
        packages, host.fact.apk_packages, present,
        install_command='apk add',
        uninstall_command='apk remove',
        upgrade_command='apk upgrade',
        version_join='=',
        latest=latest,
    )
