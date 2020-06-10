'''
Manage brew packages on mac/OSX. See https://brew.sh/
'''

from pyinfra.api import operation

from .util.packaging import ensure_packages


@operation
def update(state, host):
    '''
    Updates brew repositories.
    '''

    yield 'brew update'

_update = update  # noqa: E305


@operation
def upgrade(state, host):
    '''
    Upgrades all brew packages.
    '''

    yield 'brew upgrade'

_upgrade = upgrade  # noqa: E305


@operation
def packages(
    state, host,
    packages=None, present=True, latest=False,
    update=False, upgrade=False,
):
    '''
    Add/remove/update brew packages.

    + packages: list of packages to ensure
    + present: whether the packages should be installed
    + latest: whether to upgrade packages without a specified version
    + update: run brew update before installing packages
    + upgrade: run brew upgrade before installing packages

    Versions:
        Package versions can be pinned like brew: ``<pkg>@<version>``.

    Examples:

    .. code:: python

        # Update package list and install packages
        brew.packages(
            {'Install Vim and vimpager'},
            ['vimpager', 'vim'],
            update=True,
        )

        # Install the latest versions of packages (always check)
        brew.packages(
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
        packages, host.fact.brew_packages, present,
        install_command='brew install',
        uninstall_command='brew uninstall',
        upgrade_command='brew upgrade',
        version_join='@',
        latest=latest,
    )


@operation
def cask_upgrade(state, host):
    '''
    Upgrades all brew casks.
    '''

    yield 'brew cask upgrade'


@operation
def casks(
    state, host,
    packages=None, present=True, latest=False, upgrade=False,
):
    '''
    Add/remove/update brew casks.

    + packages: list of packages to ensure
    + present: whether the packages should be installed
    + latest: whether to upgrade packages without a specified version
    + upgrade: run brew cask upgrade before installing packages

    Versions:
        Package versions can be pinned like brew: ``<pkg>@<version>``.

    Example:

    .. code:: python

        brew.casks(
            {'Upgrade and install the latest package via casks'},
            ['godot'],
            upgrade=True,
            latest=True,
        )

    '''

    if upgrade:
        yield cask_upgrade(state, host)

    yield ensure_packages(
        packages, host.fact.brew_casks, present,
        install_command='brew cask install',
        uninstall_command='brew cask uninstall',
        upgrade_command='brew cask upgrade',
        version_join='@',
        latest=latest,
    )


@operation
def tap(state, host, name, present=True):
    '''
    Add/remove brew taps.

    + name: the name of the tasp
    + present: whether this tap should be present or not

    Examples:

    .. code:: python

        brew.tap(
            {'Add a brew tap'},
            'includeos/includeos',
        )

        # multiple taps
        taps = ['includeos/includeos', 'ktr0731/evans']
        for tap in taps:
            brew.tap(
                {f'Add brew tap {tap}'},
                tap,
            )

    '''

    taps = host.fact.brew_taps
    is_tapped = name in taps

    if present and not is_tapped:
        yield 'brew tap {0}'.format(name)

    elif not present and is_tapped:
        yield 'brew untap {0}'.format(name)
