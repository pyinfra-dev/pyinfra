"""
Manage Portage packages. (Gentoo Linux package manager)
"""

from __future__ import annotations

from pyinfra import host
from pyinfra.api import operation
from pyinfra.facts.portage import (
    PortageMaskedPackages,
    PortagePackages,
    PortageUpgradeablePackages,
)
from pyinfra.facts.util.packages import build_package_map

from .util.packaging import ensure_packages


def _portage_version_format(name: str, operator: str, version: str) -> str:
    """Format versioned package atom for emerge: =category/package-version."""
    return f"={name}-{version}"


@operation()
def upgrade():
    """
    Upgrades all Portage packages (``emerge -uDN @world``).

    This operation is idempotent: it checks for available upgrades first
    and only runs the upgrade when upgradeable packages exist.
    """

    upgradeable = host.get_fact(PortageUpgradeablePackages)
    if not upgradeable:
        host.noop("all packages are up to date")
        return

    yield "emerge -uDN @world"


_upgrade = upgrade._inner  # noqa: E305


@operation(is_idempotent=False)
def update():
    """
    Syncs Portage repositories (``emerge --sync``).
    """

    yield "emerge --sync"


_update = update._inner  # noqa: E305


@operation()
def packages(
    packages: str | list[str] | None = None,
    present=True,
    update=False,
    upgrade=False,
    latest=False,
):
    """
    Add/remove Portage packages.

    + packages: list of packages to ensure (use ``category/name`` format)
    + present: whether the packages should be installed
    + update: run ``emerge --sync`` before installing packages
    + upgrade: run ``emerge -uDN @world`` before installing packages
    + latest: upgrade installed packages that have available updates

    Versions:
        Package versions can be pinned: ``sys-devel/gcc=11.2.0``.
        This translates to ``=sys-devel/gcc-11.2.0`` in the emerge command.

    **Example:**

    .. code:: python

        from pyinfra.operations import portage
        portage.packages(
            name="Install GCC and Vim",
            packages=["sys-devel/gcc", "app-editors/vim"],
        )
    """

    if update:
        yield from _update()

    if upgrade:
        yield from _upgrade()

    installed = host.get_fact(PortagePackages)
    upgradeable = host.get_fact(PortageUpgradeablePackages)
    masked = host.get_fact(PortageMaskedPackages)

    current_packages = build_package_map(installed, upgradeable, set(masked))

    yield from ensure_packages(
        host,
        packages,
        current_packages,
        present,
        install_command="emerge",
        uninstall_command="emerge --depclean",
        upgrade_command="emerge",
        latest=latest,
        version_join="=",
        inst_vers_format_fn=_portage_version_format,
    )
