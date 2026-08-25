"""
Manage brew packages on mac/OSX. See https://brew.sh/
"""

from __future__ import annotations

import urllib.parse

from pyinfra import host
from pyinfra.api import operation
from pyinfra.api.command import QuoteString, StringCommand
from pyinfra.api.exceptions import OperationValueError
from pyinfra.facts.brew import (
    BrewCasks,
    BrewItemKind,
    BrewPackages,
    BrewTaps,
    BrewTrusted,
    BrewVersion,
    _new_cask_cli,
)

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


@operation()
def packages(
    packages: str | list[str] | None = None,
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

        from pyinfra.operations import brew
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
        yield from _update._inner()

    if upgrade:
        yield from _upgrade._inner()

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


def cask_args():
    return ("", " --cask") if _new_cask_cli(host.get_fact(BrewVersion)) else ("cask ", "")


@operation(is_idempotent=False)
def cask_upgrade():
    """
    Upgrades all brew casks.
    """

    yield "brew {}upgrade{}".format(*cask_args())


@operation()
def casks(
    casks: str | list[str] | None = None,
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
        yield from cask_upgrade._inner()

    args = cask_args()

    yield from ensure_packages(
        host,
        casks,
        host.get_fact(BrewCasks),
        present,
        install_command="brew {}install{}".format(*args),
        uninstall_command="brew {}uninstall{}".format(*args),
        upgrade_command="brew {}upgrade{}".format(*args),
        version_join="@",
        latest=latest,
    )


@operation()
def tap(
    src: str | None = None,
    present: bool = True,
    trusted: bool | None = False,
    url: str | None = None,
):
    """
    Add/remove brew taps.

    + src: the name of the tap
    + present: whether this tap should be present or not. Default True.
    + trusted: whether or not this tap should be trusted.  Default False.
    + url: the url of the tap. See https://docs.brew.sh/Taps

    **Examples:**

    .. code:: python

        brew.tap(
            name="Add a brew tap",
            src="includeos/includeos",
            trusted=True,
        )

        # Just url is equivalent to
        # `brew tap kptdev/kpt https://github.com/kptdev/kpt`
        brew.tap(
            url="https://github.com/kptdev/kpt",
            trusted=True,
        )

        # src and url is equivalent to
        # `brew tap example/project https://github.example.com/project`
        brew.tap(
            src="example/project",
            url="https://github.example.com/project",
            trusted=True,
        )

        # Multiple taps
        for tap in ["includeos/includeos", "ktr0731/evans"]:
            brew.tap(
                name={f"Add brew tap {tap}"},
                src=tap,
                trusted=True,
            )

    """

    def mk_trust_cmd(tap: str, *, trust: bool | None = None) -> StringCommand:
        return StringCommand("brew", "trust" if trust else "untrust", "--tap", QuoteString(tap))

    trusted = trusted or False

    if not (src or url):
        host.noop("no tap was specified")
        return

    src = src or str(urllib.parse.urlparse(url).path).strip("/")

    if len(src.split("/")) != 2:
        host.noop(f"src '{src}' doesn't have two components.")
        return

    taps = host.get_fact(BrewTaps)
    already_tapped = src in taps

    if present and already_tapped:
        host.noop(f"tap {src} already exists")
        trusted_taps = host.get_fact(BrewTrusted).get("taps", [])
        if (trusted and (src not in trusted_taps)) or ((not trusted) and (src in trusted_taps)):
            yield mk_trust_cmd(src, trust=trusted)
        return

    if already_tapped:
        yield StringCommand("brew", "untap", QuoteString(src))
        return

    if not present:
        host.noop(f"tap {src} does not exist")
        return

    args = [QuoteString(src)]
    if url is not None:
        args.append(QuoteString(url))

    yield StringCommand("brew", "tap", *args)

    if trusted:  # if not already present, can't be trusted so no check of BrewTrusted
        yield mk_trust_cmd(src, trust=True)

    return


TRUST_SRC_AND_OPTION = {
    BrewItemKind.CASK: "--cask",
    BrewItemKind.COMMAND: "--command",
    BrewItemKind.FORMULA: "--formula",
    BrewItemKind.TAP: "--tap",
}


@operation()
def trust(items: str | list[str], kind: BrewItemKind, trusted: bool):
    """
    Trust/untrust brew casks, commands, formulae and/or taps (see https://docs.brew.sh/Tap-Trust)

    + items: the cask, command, formula or tap to be trusted or untrusted
    + kind: whether the item is a CASK, COMMAND, FORMULA or TAP (using BrewItemKind enum)
    + trusted: whether this item should be trusted or not.  no default, must be specified

    **Examples:**

    .. code:: python

        brew.trust(
            name="Mark magic tap as trusted",
            items="includeos/includeos",
            kind=BrewItemKind.TAP,
            trusted=True
        )
    """
    item_set = set(items if isinstance(items, list) else [items])
    if any(len(item) < 1 for item in item_set):
        raise OperationValueError("all items must have non-zero length names")
    desired_state = "trust" if trusted else "untrust"
    trusted_items = set(host.get_fact(BrewTrusted).get(kind.value, []))
    found = item_set & trusted_items
    need_to_change = (item_set - found) if trusted else found
    already_ok = item_set - need_to_change

    for item in sorted(need_to_change):
        yield StringCommand("brew", desired_state, TRUST_SRC_AND_OPTION[kind], QuoteString(item))
    if len(already_ok) > 0:
        host.noop(f"{', '.join(sorted(already_ok))} {kind.value} already {desired_state}ed")
