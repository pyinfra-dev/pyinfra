"""
Manage apk packages. (Alpine Linux)
"""

from __future__ import annotations

from pyinfra import host
from pyinfra.api import operation
from pyinfra.facts.apk import ApkHeldPackages, ApkPackages, ApkUpgradeablePackages
from pyinfra.facts.util.packages import build_package_map

from .util.packaging import ensure_packages


@operation()
def upgrade(available: bool = False):
    """
    Upgrades all apk packages.

    + available: force all packages to be upgraded (recommended on whole Alpine version upgrades)

    This operation is idempotent - it will noop if no upgradeable packages are found.
    """

    upgradeable = host.get_fact(ApkUpgradeablePackages)

    # Check if there are any upgradeable packages using iteration
    has_upgradeable = any(True for _ in upgradeable)
    if not has_upgradeable:
        host.noop("all packages are up to date")
        return

    if available:
        yield "apk upgrade --available"
    else:
        yield "apk upgrade"


_upgrade = upgrade._inner  # noqa: E305


@operation(is_idempotent=False)
def update():
    """
    Updates apk repositories.
    """

    yield "apk update"


_update = update._inner  # noqa: E305


@operation()
def packages(
    packages: str | list[str] | None = None,
    present=True,
    latest=False,
    update=False,
    upgrade=False,
):
    """
    Add/remove/update apk packages.

    + packages: list of packages to ensure
    + present: whether the packages should be installed
    + latest: whether to upgrade packages without a specified version
    + update: run ``apk update`` before installing packages
    + upgrade: run ``apk upgrade`` before installing packages

    Versions:
        Package versions can be pinned like apk: ``<pkg>=<version>``.

    **Examples:**

    .. code:: python

        from pyinfra.operations import apk
        # Update package list and install packages
        apk.packages(
            name="Install Asterisk and Vim",
            packages=["asterisk", "vim"],
            update=True,
        )

        # Install the latest versions of packages (always check)
        apk.packages(
            name="Install latest Vim",
            packages=["vim"],
            latest=True,
        )
    """

    if update:
        yield from _update()

    if upgrade:
        yield from _upgrade()

    installed = host.get_fact(ApkPackages)
    upgradeable = host.get_fact(ApkUpgradeablePackages)
    held = host.get_fact(ApkHeldPackages)

    current_packages = build_package_map(installed, upgradeable, set(held))

    yield from ensure_packages(
        host,
        packages,
        current_packages,
        present,
        install_command="apk add",
        uninstall_command="apk del",
        upgrade_command="apk upgrade",
        version_join="=",
        latest=latest,
    )
