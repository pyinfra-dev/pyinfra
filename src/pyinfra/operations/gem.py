"""
Manage Ruby gem packages. (see https://rubygems.org/ )
"""

from __future__ import annotations

from pyinfra import host
from pyinfra.api import operation
from pyinfra.facts.gem import GemOutdatedPackages, GemPackages

from pyinfra.facts.util.packages import build_package_map

from .util.packaging import ensure_packages


@operation()
def packages(packages: str | list[str] | None = None, present=True, latest=False):
    """
    Add/remove/update gem packages.

    + packages: list of packages to ensure
    + present: whether the packages should be installed
    + latest: whether to upgrade packages without a specified version

    Versions:
        Package versions can be pinned like gem: ``<pkg>:<version>``.

    **Example:**

    .. code:: python

        from pyinfra.operations import gem
        # Note: Assumes that 'gem' is installed.
        gem.packages(
            name="Install rspec",
            packages=["rspec"],
        )
    """

    installed_packages = host.get_fact(GemPackages)
    outdated_packages = host.get_fact(GemOutdatedPackages)
    current_packages = build_package_map(installed_packages, outdated_packages)

    yield from ensure_packages(
        host,
        packages,
        current_packages,
        present,
        install_command="gem install",
        uninstall_command="gem uninstall",
        upgrade_command="gem update",
        version_join=":",
        latest=latest,
    )
