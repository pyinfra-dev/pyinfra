"""
Manage pipx (python) applications.
"""

from pyinfra import host
from pyinfra.api import OperationError, operation
from pyinfra.facts.pipx import PipxEnvironment, PipxPackages
from pyinfra.facts.server import Path

from .util.packaging import ensure_packages


@operation
def packages(
    packages=None,
    present=True,
    latest=False,
    requirements=None,
    pipx="pipx",
    extra_install_args=None,
):
    """
    Install/remove/update pipx packages.

    + packages: list of packages to ensure
    + present: whether the packages should be installed
    + latest: whether to upgrade packages without a specified version
    + pipx: name or path of the pipx binary to use
    + extra_install_args: additional arguments to the pipx install command

    Versions:
        Package versions can be pinned like pip: ``<pkg>==<version>``.

    **Example:**

    .. code:: python

        pipx.packages(
            name="Install ",
            packages=["pyinfra"],
        )
    """

    # We should always use the --force flag because
    # if install it's called, that meen the version missmatch
    # so we need the --force flag to get the good version installed
    install_command = [pipx, "install", "--force"]
    if extra_install_args:
        install_command.append(extra_install_args)
    install_command = " ".join(install_command)

    uninstall_command = " ".join([pipx, "uninstall"])
    upgrade_command = " ".join([pipx, "upgrade"])

    # Handle passed in packages
    if packages:
        current_packages = host.get_fact(PipxPackages, pipx=pipx)

        if current_packages is None:
            raise OperationError("Unable to get pipx packages")

        # pipx support only one package name at a time
        for package in packages:
            yield from ensure_packages(
                host,
                [package],
                current_packages,
                present,
                install_command=install_command,
                uninstall_command=uninstall_command,
                upgrade_command=upgrade_command,
                version_join="==",
                latest=latest,
            )


@operation
def upgrade_all(pipx="pipx"):
    """
    Upgrade all pipx packages.
    """
    yield f"{pipx} upgrade-all"


@operation
def ensure_path(pipx="pipx"):
    """
    Ensure pipx bin dir is in the PATH.
    """

    # Fetch the current user's PATH
    path = host.get_fact(Path)
    # Fetch the pipx environment variables
    pipx_env = host.get_fact(PipxEnvironment)

    # If the pipx bin dir is already in the user's PATH, we're done
    if pipx_env["PIPX_BIN_DIR"] in path.split(":"):
        host.noop("pipx bin dir is already in the PATH")
    else:
        yield f"{pipx} ensurepath"
