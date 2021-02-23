'''
Manage apk packages.
'''

from pyinfra.api import operation

from .util.packaging import ensure_packages


@operation
def upgrade(state=None, host=None):
    '''
    Upgrades all apk packages.
    '''

    yield 'apk upgrade'

_upgrade = upgrade  # noqa: E305


@operation
def update(state=None, host=None):
    '''
    Updates apk repositories.
    '''

    yield 'apk update'

_update = update  # noqa: E305


@operation
def packages(
    packages=None, present=True, latest=False,
    update=False, upgrade=False,
    state=None, host=None,
):
    '''
    Add/remove/update apk packages.

    + packages: list of packages to ensure
    + present: whether the packages should be installed
    + latest: whether to upgrade packages without a specified version
    + update: run ``apk update`` before installing packages
    + upgrade: run ``apk upgrade`` before installing packages

    Versions:
        Package versions can be pinned like apk: ``<pkg>=<version>``.

    Examples:

    .. code:: python

        # Update package list and install packages
        apk.packages(
            name='Install Asterisk and Vim',
            packages=['asterisk', 'vim'],
            update=True,
        )

        # Install the latest versions of packages (always check)
        apk.packages(
            name='Install latest Vim',
            packages=['vim'],
            latest=True,
        )
    '''

    if update:
        yield _update(state=state, host=host)

    if upgrade:
        yield _upgrade(state=state, host=host)

    yield ensure_packages(
        host, packages, host.fact.apk_packages, present,
        install_command='apk add',
        uninstall_command='apk del',
        upgrade_command='apk upgrade',
        version_join='=',
        latest=latest,
    )
