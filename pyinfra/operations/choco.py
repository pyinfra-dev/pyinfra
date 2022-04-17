"""
Manage ``choco`` (Chocolatey) packages (https://chocolatey.org).
"""

from pyinfra import host
from pyinfra.api import operation
from pyinfra.facts.choco import ChocoPackages

from .util.packaging import ensure_packages


@operation
def packages(packages=None, present=True, latest=False):
    """
    Add/remove/update ``choco`` packages.

    + packages: list of packages to ensure
    + present: whether the packages should be installed
    + latest: whether to upgrade packages without a specified version

    Versions:
        Package versions can be pinned like gem: ``<pkg>:<version>``.

    **Example:**

    .. code:: python

        # Note: Assumes that 'choco' is installed and
        #       user has Administrator permission.
        choco.packages(
            name="Install Notepad++",
            packages=["notepadplusplus"],
        )
    """

    yield from ensure_packages(
        host,
        packages,
        host.get_fact(ChocoPackages),
        present,
        install_command="choco install -y",
        uninstall_command="choco uninstall -y -x",
        upgrade_command="choco update -y",
        version_join=":",
        latest=latest,
    )


@operation(is_idempotent=False)
def install():
    """
    Install ``choco`` (Chocolatey).
    """

    yield "Set-ExecutionPolicy Bypass -Scope Process -Force ;" "iex ((New-Object System.Net.WebClient).DownloadString" '("https://chocolatey.org/install.ps1"))'  # noqa
