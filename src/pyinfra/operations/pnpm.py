"""
Manage pnpm (Node.js) packages. See https://pnpm.io/

Operations taking a ``directory`` run pnpm inside it rather than under pnpm's
``--dir``, so corepack - which resolves the pnpm version from the working
directory - picks up the project's ``packageManager`` pin. No ``_chdir`` needed.
"""

from __future__ import annotations

from typing import Literal

from pyinfra import host
from pyinfra.api import OperationError, QuoteString, StringCommand, operation
from pyinfra.facts.pnpm import PNPM_CMD, PnpmModulesUpToDate, PnpmPackages

from .util.packaging import PkgInfo, ensure_packages


def _parse_package(package: str) -> PkgInfo:
    """
    Split a ``<name>[@<version>]`` package into its name and version.

    A leading ``@`` starts a scope (eg ``@types/node``), so only an ``@`` past the
    first character separates the two. ``latest`` is pnpm's default dist-tag, so it
    counts as no version - which keeps ``<pkg>@latest`` idempotent.
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


def _in_directory(directory: str) -> list[str | QuoteString]:
    """Start a pnpm command that runs *in* ``directory`` - see the module docstring."""

    return ["cd", QuoteString(directory), "&&", PNPM_CMD]


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
        Pin like pnpm: ``<pkg>@<version>``. Only exact versions are compared against
        the installed ones, so ranges and dist-tags (eg ``<pkg>@^5``) re-apply on
        every run.

    Note:
        Packages match by name across every dependency group, so one already
        installed as a (dev/optional) dependency stays where it is rather than
        moving. ``latest=True`` upgrades via ``pnpm update --latest``, ignoring the
        ranges in ``package.json``; with no local version to compare against the
        newest published one, it always reports as changed.

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

    pnpm_command: list[str | QuoteString] = (
        [PNPM_CMD, "--global"] if directory is None else _in_directory(directory)
    )

    install_parts: list[str | QuoteString] = [*pnpm_command, "add"]
    if dev:
        install_parts.append("--save-dev")

    package_infos = [_parse_package(package) for package in packages]
    if not present:
        # The version still has to match what's installed, just not appear in the command.
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


@operation()
def install(
    directory: str,
    *,
    frozen_lockfile: bool | None = None,
    ignore_scripts: bool = False,
    package_import_method: Literal["auto", "clone", "copy", "hardlink"] | None = None,
):
    """
    Install every dependency a project declares, as resolved by its lockfile.

    + directory: project directory holding ``package.json`` and ``pnpm-lock.yaml``
    + frozen_lockfile: fail rather than update an outdated lockfile, defaults to pnpm's own
      behaviour of doing so on CI only
    + ignore_scripts: don't run lifecycle scripts of the project or the installed packages
    + package_import_method: how packages are placed into ``node_modules`` from the store,
      one of ``auto`` (default), ``hardlink``, ``clone`` or ``copy``

    Note:
        The install is skipped when ``node_modules`` was already built from the lockfile
        now in the directory, so ``package.json`` edits not yet written to
        ``pnpm-lock.yaml`` are missed - deploy both files together.

    **Example:**

    .. code:: python

        pnpm.install(
            name="Install app dependencies",
            directory="/opt/app",
            package_import_method="hardlink",
        )
    """

    if host.get_fact(PnpmModulesUpToDate, directory=directory):
        host.noop(f"node_modules in {directory} is up to date")
        return

    install_parts: list[str | QuoteString] = [*_in_directory(directory), "install"]

    if frozen_lockfile is not None:
        install_parts.append("--frozen-lockfile" if frozen_lockfile else "--no-frozen-lockfile")
    if ignore_scripts:
        install_parts.append("--ignore-scripts")
    if package_import_method is not None:
        install_parts.extend(("--package-import-method", QuoteString(package_import_method)))

    yield StringCommand(*install_parts)


@operation()
def run(
    script: str,
    directory: str,
    *,
    args: str | list[str] | None = None,
    if_present: bool = False,
):
    """
    Run one of a project's ``package.json`` scripts.

    + script: name of the script to run
    + directory: project directory holding ``package.json``
    + args: argument(s) to append to the script's own command line, one per item
    + if_present: succeed quietly when the project has no such script, instead of failing

    Not idempotent: the script runs on every deploy. To build only when something new
    arrived, gate it with ``_if`` on whatever delivered the source - the checkout, not
    the dependency install, which reports no change when only application code moved.

    **Example:**

    .. code:: python

        checkout = git.repo(src="git@github.com:me/app.git", dest="/opt/app", branch=VERSION)
        pnpm.install(directory="/opt/app")

        pnpm.run(
            name="Build the app",
            script="build",
            directory="/opt/app",
            _if=checkout.did_change,
        )
    """

    run_parts: list[str | QuoteString] = [*_in_directory(directory), "run"]

    # pnpm forwards everything after the script name to the script, so its flags come first.
    if if_present:
        run_parts.append("--if-present")

    run_parts.append(QuoteString(script))

    if args is not None:
        if isinstance(args, str):
            args = [args]
        run_parts.extend(QuoteString(arg) for arg in args)

    yield StringCommand(*run_parts)
