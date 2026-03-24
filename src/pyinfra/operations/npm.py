"""
Manage npm (aka node aka Node.js) packages.
"""

from __future__ import annotations

import shlex

from pyinfra import host
from pyinfra.api import operation
from pyinfra.facts.npm import NpmOutdatedPackages, NpmPackages

from pyinfra.facts.util.packages import build_package_map

from .util.packaging import ensure_packages


@operation()
def packages(
    packages: str | list[str] | None = None,
    present=True,
    latest=False,
    directory: str | None = None,
):
    """
    Install/remove/update npm packages.

    + packages: list of packages to ensure
    + present: whether the packages should be present
    + latest: whether to upgrade packages without a specified version
    + directory: directory to manage packages for, defaults to global

    Versions:
        Package versions can be pinned like npm: ``<pkg>@<version>``.
    """

    installed_packages = host.get_fact(NpmPackages, directory=directory)
    outdated_packages = host.get_fact(NpmOutdatedPackages, directory=directory)
    current_packages = build_package_map(installed_packages, outdated_packages)

    install_command = (
        "npm install -g"
        if directory is None
        else "cd {0} && npm install".format(shlex.quote(directory))
    )

    uninstall_command = (
        "npm uninstall -g"
        if directory is None
        else "cd {0} && npm uninstall".format(shlex.quote(directory))
    )

    upgrade_command = (
        "npm update -g"
        if directory is None
        else "cd {0} && npm update".format(shlex.quote(directory))
    )

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
