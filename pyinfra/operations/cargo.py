"""
Manage cargo (aka Rust) packages.
"""

from pyinfra import host
from pyinfra.api import operation
from pyinfra.facts.cargo import CargoPackages

from .util.packaging import ensure_packages


@operation
def packages(packages=None, present=True, latest=False):
    """
    Install/remove/update cargo packages.

    + packages: list of packages to ensure
    + present: whether the packages should be present
    + latest: whether to upgrade packages without a specified version

    Versions:
        Package versions can be pinned like cargo: ``<pkg>@<version>``.
    """

    current_packages = host.get_fact(CargoPackages)

    install_command = "cargo install"

    uninstall_command = "cargo uninstall"

    upgrade_command = "cargo install"

    yield from ensure_packages(
        host,
        packages,
        current_packages,
        present,
        install_command=install_command,
        uninstall_command=uninstall_command,
        upgrade_command=upgrade_command,
        version_join="@",
        latest=latest,
    )
