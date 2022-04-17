"""
Manage npm (aka node aka Node.js) packages.
"""

from pyinfra import host
from pyinfra.api import operation
from pyinfra.facts.npm import NpmPackages

from .util.packaging import ensure_packages


@operation
def packages(packages=None, present=True, latest=False, directory=None):
    """
    Install/remove/update npm packages.

    + packages: list of packages to ensure
    + present: whether the packages should be present
    + latest: whether to upgrade packages without a specified version
    + directory: directory to manage packages for, defaults to global

    Versions:
        Package versions can be pinned like npm: ``<pkg>@<version>``.
    """

    current_packages = host.get_fact(NpmPackages, directory=directory)

    install_command = (
        "npm install -g" if directory is None else "cd {0} && npm install".format(directory)
    )

    uninstall_command = (
        "npm uninstall -g" if directory is None else "cd {0} && npm uninstall".format(directory)
    )

    upgrade_command = (
        "npm update -g" if directory is None else "cd {0} && npm update".format(directory)
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
