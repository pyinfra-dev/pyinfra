"""
Manage Paludis packages. (Exherbo Linux package manager)
"""

from __future__ import annotations

from pyinfra import host
from pyinfra.api import operation
from pyinfra.facts.paludis import PaludisPackages

from .util.packaging import ensure_packages


def _paludis_version_format(name: str, operator: str, version: str) -> str:
    """Format versioned package for cave: =category/package-version."""
    return f"={name}-{version}"


@operation()
def upgrade():
    """
    Upgrades all Paludis packages (``cave resolve -c -x world``).
    """

    yield "cave resolve -c -x world"


_upgrade = upgrade._inner  # noqa: E305


@operation(is_idempotent=False)
def update():
    """
    Syncs Paludis repositories (``cave sync``).
    """

    yield "cave sync"


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
    Add/remove Paludis packages.

    + packages: list of packages to ensure (use ``category/name`` format)
    + present: whether the packages should be installed
    + update: run ``cave sync`` before installing packages
    + upgrade: run ``cave resolve -c -x world`` before installing packages
    + latest: whether to upgrade packages without a specified version

    Versions:
        Package versions can be pinned: ``sys-apps/systemd=249``.
        This translates to ``=sys-apps/systemd-249`` in the cave command.

    **Example:**

    .. code:: python

        from pyinfra.operations import paludis
        paludis.packages(
            name="Install systemd",
            packages=["sys-apps/systemd"],
        )
    """

    if update:
        yield from _update()

    if upgrade:
        yield from _upgrade()

    installed = host.get_fact(PaludisPackages)

    yield from ensure_packages(
        host,
        packages,
        installed,
        present,
        install_command="cave resolve -x",
        uninstall_command="cave uninstall -x",
        latest=latest,
        version_join="=",
        inst_vers_format_fn=_paludis_version_format,
    )
