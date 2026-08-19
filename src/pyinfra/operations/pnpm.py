"""
Manage pnpm (Node.js) packages. See https://pnpm.io/
"""

from __future__ import annotations

from pyinfra import host
from pyinfra.api import OperationError, QuoteString, StringCommand, operation
from pyinfra.facts.pnpm import PNPM_CMD, PnpmPackages

from .util.packaging import PkgInfo, ensure_packages


def _parse_package(package: str) -> PkgInfo:
    """
    Split a ``<name>[@<version>]`` package into its name and version.

    A leading ``@`` starts a scope (eg ``@types/node``), so only an ``@`` after
    the first character separates the two. ``latest`` is the dist-tag pnpm
    installs by default, so it is treated as no version at all - which keeps
    ``<pkg>@latest`` idempotent.
    """

    index = package.rfind("@", 1)
    if index == -1:
        return PkgInfo(package, "", "@", "")

    name, version = package[:index], package[index + 1 :]
    return PkgInfo(name, "" if version == "latest" else version, "@", "")


def _drop_version(name: str, operator: str, version: str) -> str:
    """
    Render a package as its bare name - ``pnpm remove`` rejects the
    ``<pkg>@<version>`` form ``pnpm add`` takes.
    """

    return name


@operation()
def packages(
    packages: str | list[str] | None = None,
    present: bool = True,
    latest: bool = False,
    directory: str | None = None,
    dev: bool = False,
):
    """
    Install/remove/update pnpm packages.

    + packages: list of packages to ensure
    + present: whether the packages should be present
    + latest: whether to upgrade packages without a specified version
    + directory: directory to manage packages for, defaults to global
    + dev: add the packages as development dependencies, requires ``directory``

    Versions:
        Package versions can be pinned like pnpm: ``<pkg>@<version>``. Only
        exact versions are compared against the installed ones, so ranges and
        dist-tags (eg ``<pkg>@^5``) are re-applied on every run.

    Note:
        Packages are matched by name across every dependency group, so a
        package already installed as a (dev/optional) dependency is left where
        it is rather than moved. ``latest=True`` upgrades with
        ``pnpm update --latest``, which ignores the ranges in ``package.json``,
        and always reports as changed - there is no local version to compare
        the newest published one against.

    **Example:**

    .. code:: python

        pnpm.packages(
            name="Install typescript for the app",
            packages=["typescript@5.4.5"],
            directory="/opt/app",
            dev=True,
        )
    """

    if dev and directory is None:
        raise OperationError("pnpm has no global dev dependencies, `directory` is required")

    if packages is None:
        return
    if isinstance(packages, str):
        packages = [packages]

    pnpm_command: list[str | QuoteString] = [PNPM_CMD]
    if directory is None:
        pnpm_command.append("--global")
    else:
        pnpm_command.extend(("--dir", QuoteString(directory)))

    install_parts: list[str | QuoteString] = [*pnpm_command, "add"]
    if dev:
        install_parts.append("--save-dev")

    package_infos = [_parse_package(package) for package in packages]
    if not present:
        # Any version still has to match the installed one, it just can't be
        # part of the removal command itself.
        package_infos = [info._replace(inst_vers_format_fn=_drop_version) for info in package_infos]

    yield from ensure_packages(
        host,
        package_infos,
        host.get_fact(PnpmPackages, directory=directory),
        present,
        install_command=StringCommand(*install_parts),
        uninstall_command=StringCommand(*pnpm_command, "remove"),
        upgrade_command=StringCommand(*pnpm_command, "update", "--latest"),
        latest=latest,
    )
