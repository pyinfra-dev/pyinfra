"""
Manage brew packages on mac/OSX. See https://brew.sh/
"""

from pyinfra import host
from pyinfra.api import operation
from pyinfra.facts.brew import BrewCasks, BrewPackages, BrewTaps, BrewVersion, new_cask_cli

from .util.packaging import ensure_packages


@operation(is_idempotent=False)
def update():
    """
    Updates brew repositories.
    """

    yield "brew update"


_update = update  # noqa: E305


@operation(is_idempotent=False)
def upgrade():
    """
    Upgrades all brew packages.
    """

    yield "brew upgrade"


_upgrade = upgrade  # noqa: E305


@operation
def packages(
    packages=None,
    present=True,
    latest=False,
    update=False,
    upgrade=False,
):
    """
    Add/remove/update brew packages.

    + packages: list of packages to ensure
    + present: whether the packages should be installed
    + latest: whether to upgrade packages without a specified version
    + update: run ``brew update`` before installing packages
    + upgrade: run ``brew upgrade`` before installing packages

    Versions:
        Package versions can be pinned like brew: ``<pkg>@<version>``.

    **Examples:**

    .. code:: python

        # Update package list and install packages
        brew.packages(
            name='Install Vim and vimpager',
            packages=["vimpager", "vim"],
            update=True,
        )

        # Install the latest versions of packages (always check)
        brew.packages(
            name="Install latest Vim",
            packages=["vim"],
            latest=True,
        )
    """

    if update:
        yield from _update()

    if upgrade:
        yield from _upgrade()

    yield from ensure_packages(
        host,
        packages,
        host.get_fact(BrewPackages),
        present,
        install_command="brew install",
        uninstall_command="brew uninstall",
        upgrade_command="brew upgrade",
        version_join="@",
        latest=latest,
    )


def cask_args(host):
    return ("", " --cask") if new_cask_cli(host.get_fact(BrewVersion)) else ("cask ", "")


@operation(
    is_idempotent=False,
    pipeline_facts={"brew_version": ""},
)
def cask_upgrade():
    """
    Upgrades all brew casks.
    """

    yield "brew %supgrade%s" % cask_args(host)


@operation(
    pipeline_facts={"brew_version": ""},
)
def casks(
    casks=None,
    present=True,
    latest=False,
    upgrade=False,
):
    """
    Add/remove/update brew casks.

    + casks: list of casks to ensure
    + present: whether the casks should be installed
    + latest: whether to upgrade casks without a specified version
    + upgrade: run brew cask upgrade before installing casks

    Versions:
        Cask versions can be pinned like brew: ``<pkg>@<version>``.

    **Example:**

    .. code:: python

        brew.casks(
            name='Upgrade and install the latest cask',
            casks=["godot"],
            upgrade=True,
            latest=True,
        )

    """

    if upgrade:
        yield from cask_upgrade()

    args = cask_args(host)

    yield from ensure_packages(
        host,
        casks,
        host.get_fact(BrewCasks),
        present,
        install_command="brew %sinstall%s" % args,
        uninstall_command="brew %suninstall%s" % args,
        upgrade_command="brew %supgrade%s" % args,
        version_join="@",
        latest=latest,
    )


@operation
def tap(src, present=True):
    """
    Add/remove brew taps.

    + src: the name of the tap
    + present: whether this tap should be present or not

    **Examples:**

    .. code:: python

        brew.tap(
            name="Add a brew tap",
            src="includeos/includeos",
        )

        # Multiple taps
        for tap in ["includeos/includeos", "ktr0731/evans"]:
            brew.tap(
                name={f"Add brew tap {tap}"},
                src=tap,
            )

    """

    taps = host.get_fact(BrewTaps)
    is_tapped = src in taps

    if present:
        if is_tapped:
            host.noop("tap {0} already exists".format(src))
        else:
            yield "brew tap {0}".format(src)
            taps.append(src)

    elif not present:
        if is_tapped:
            yield "brew untap {0}".format(src)
            taps.remove(src)
        else:
            host.noop("tap {0} does not exist".format(src))
