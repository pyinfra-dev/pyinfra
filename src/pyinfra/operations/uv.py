"""
Operations for ``uv``:
    + install, remove or upgrade Python packages
    + install, remove or upgrade  'tools'
    + create or remove virtual environments (venv's)
    + ensure the uv tool executable directory is on the PATH
"""

from __future__ import annotations

import shlex
from typing import Literal

from pyinfra import host
from pyinfra.api.command import QuoteString, StringCommand
from pyinfra.api.operation import operation
from pyinfra.facts import server
from pyinfra.facts.files import File
from pyinfra.facts.uv import (
    MANAGED_PYTHON,
    UV_CMD,
    UvInstalledPythonsByVersion,
    UvPipPackages,
    UvToolDir,
    UvTools,
)
from pyinfra.operations import files
from pyinfra.operations.util.packaging import PkgInfo, ensure_packages

# see  (see https://docs.astral.sh/uv/) for full details on uv

VENV = ".venv"
VENV_INDICATOR = f"{VENV}/bin/activate"


def addable_extras(extra_args: str | list[str] | None) -> str:
    return f" {' '.join(shlex.quote(e) for e in (extra_args or [])) if not isinstance(extra_args, str) else extra_args}"


@operation()
def packages(
    packages: str | list[str],
    *,
    requirements: str | None = None,
    present: bool = True,
    latest: bool = False,
    extra_args: str | list[str] | None = None,
):
    """
    Install/remove/update Python packages using ``uv pip``

    + packages: a package or list of packages to install/uninstall
    + requirements: optionally a path to a requirements file to install/uninstall. Default None.
    + present: whether the packages should be installed or uninstalled. Default True.
    + latest: whether to upgrade packages for which a version was not specified. Default False.
    + extra_args: zero or more additional arguments to the ``uv`` command. Default None.

    Python Package versions:
        Package versions can be specified in the `usual manner`_, e.g. ``<pkg>==<version>``.

    .. _usual manner: https://pip.pypa.io/en/stable/reference/requirement-specifiers/

    **Example:**

    .. code:: python

        uv.packages(
            name="Install Requests",
            packages=["requests"],
        )
    """
    extras = addable_extras(extra_args)
    install_command = f"{UV_CMD} pip install --no-progress{extras}"
    uninstall_command = f"{UV_CMD} pip uninstall --no-progress{extras}"
    upgrade_command = f"{UV_CMD} pip install --upgrade --no-progress{extras}"

    # (un)Install requirements
    if requirements:
        if present:
            yield f"{upgrade_command if latest else install_command} -r {requirements}"
        else:
            yield f"{uninstall_command} -r {requirements}"

    if packages:
        if isinstance(packages, str):
            packages = [packages]
        # PEP-0426 states that Python packages should be compared using lowercase, so lowercase the
        # current packages. PkgInfo.from_pep508 takes care of the package name
        current_packages = {
            pkg.lower(): version for pkg, version in host.get_fact(UvPipPackages).items()
        }

        yield from ensure_packages(
            host,
            list(filter(None, (PkgInfo.from_pep508(package) for package in packages))),
            current_packages,
            present,
            install_command=install_command,
            uninstall_command=uninstall_command,
            upgrade_command=upgrade_command,
            latest=latest,
        )

    if (not requirements) and (not packages):
        host.noop("neither packages nor requirements requested to be (un)installed")


@operation()
def pythons(
    versions: str | list[str],
    *,
    present: bool = True,
    managed: bool = True,
    extra_args: str | list[str] | None = None,
):
    """
    Install/remove Python version(s).

    + version: a version or list of Python versions
    + present: whether the versions should be installed or removed. Default True.
    + managed: whether only managed or all available version should be considered. Default True.
    + extra_args: zero or more additional arguments to be passed to ``uv``. Default None.

    **Example:**

    .. code:: python

        uv.pythons(
            name="Install Python 3.13 and 3.14",
            versions=["3.14", "3.13"],
            present=True
        )
    """
    extras = addable_extras(extra_args)
    mgd_str = MANAGED_PYTHON if managed else ""
    install_command = f"{UV_CMD} python install --no-progress {mgd_str}{extras}"
    uninstall_command = f"{UV_CMD} python uninstall --no-progress {mgd_str}{extras}"
    current_versions = host.get_fact(UvInstalledPythonsByVersion, managed)

    if versions:
        # uv supports only one Python version at a time
        for version in [versions] if isinstance(versions, str) else versions:
            yield from ensure_packages(
                host,
                [version],
                current_versions,
                present,
                install_command=install_command,
                uninstall_command=uninstall_command,
            )
    else:
        host.noop("no Python versions requested to be (un)installed")


@operation()
def tools(
    tools: str | list[str],
    *,
    present: bool = True,
    latest: bool = False,
    extra_args: str | list[str] | None = None,
):
    """
    Install/remove/update packages using ``uv tool``.

    + tools: a package or list of packages to install as tools
    + present: whether the packages should be installed or uninstalled.  Default True.
    + latest: whether or not to upgrade packages without a specified version. Default False.
    + extra_args: zero or more additional arguments to ``uv``. Default None.

    Versions:
        Tool versions may be, but are not required to be, specified in the
        `usual manner`_: ``<pkg>==<version>``.

    **Example:**

    .. code:: python

        uv.tools(
            name="Install Pyinfra",
            tools=["pyinfra"],
            present=True
        )
    """
    extras = addable_extras(extra_args)
    install_command = f"{UV_CMD} tool install --no-progress{extras}"
    uninstall_command = f"{UV_CMD} tool uninstall --no-progress{extras}"
    upgrade_command = f"{UV_CMD} tool install --upgrade --no-progress{extras}"

    already_installed = {pkg.lower(): version for pkg, version in host.get_fact(UvTools).items()}

    # uv tool install supports only one package name at a time
    if tools:
        for tool in [tools] if isinstance(tools, str) else tools:
            if (pkg_info := PkgInfo.from_pep508(tool)) is None:
                continue  # PkgInfo.from_pep508 logged a warning
            yield from ensure_packages(
                host,
                [pkg_info],
                already_installed,
                present,
                install_command=install_command,
                uninstall_command=uninstall_command,
                upgrade_command=upgrade_command,
                latest=latest,
            )
    else:
        host.noop("no tools requested to be (un)installed")


@operation()
def tools_upgrade_all(*, extra_args: str | list[str] | None = None):
    """
    Upgrade all ``uv`` tools.

    + extra_args: zero or more additional arguments to ``uv``. Default None.
    """
    extras = addable_extras(extra_args)
    yield f"{UV_CMD} tool upgrade --all{extras}"


@operation()
def tools_update_shell():
    """
    Ensure that the ``uv`` tool executable directory is on the `PATH`.
    """
    if host.get_fact(UvToolDir) in host.get_fact(server.Path).split(":"):
        host.noop(f"{UV_CMD} bin dir is already in the PATH")
    else:
        yield f"{UV_CMD} tool update-shell"


@operation()
def venv(
    path: str,
    *,
    present: bool = True,
    python: str | None = None,
    allow_existing: bool = False,
    clear_existing: bool = False,
    link_mode: Literal["clone", "copy", "hardlink", "symlink"] | None = None,
    seed: bool = False,
    site_packages: bool = False,
    extra_args: str | list[str] | None = None,
):
    """
    Add/remove a Python venv in the specified location.

    + path: where to create the venv
    + present: whether the venv should be created or removed.  Default True
    + python: Python interpreter to use. Defaults to not specified.
    + allow_existing: allow (and retain) existing files in the venv directory. Default False
    + clear_existing: remove all existing files in the venv directory. Default False
    + seed: whether to seed the venv with ``pip``, and pre-3.12, ``setuptools`` and ``wheel``.
      Default False
    + site_packages: give the venv access to the global site-packages. Default False
    + link_mode: method to use when installing seed packages: clone, copy, hardlink or symlink.
      Default is platform-dependent
    + extra_args: zero or more additional arguments to the `'uv`' command

    **Example:**

    .. code:: python

        uv.venv(
            name="Create a venv",
            path="/my/projects/useful-project/.venv",
        )
    """
    #    https://docs.astral.sh/uv/reference/cli/#uv-venv

    exists = host.get_fact(File, path=f"{path}/{VENV_INDICATOR}")

    if present:
        if allow_existing and clear_existing:
            raise ValueError("allow_existing and clear_existing cannot both be set")
        if len(str(path).strip()) == 0:
            raise ValueError("must provide path in which .venv is to be created")
        if exists:
            host.noop(f"venv already exists at {path}")
        else:
            cmd_list: list[str | QuoteString] = [UV_CMD, "venv"]
            if allow_existing:
                cmd_list.append("--allow-existing")
            if clear_existing:
                cmd_list.append("--clear")
            if seed:
                cmd_list.append("--seed")
            if link_mode:
                cmd_list.extend(["--link-mode", QuoteString(link_mode)])
            if site_packages:
                cmd_list.append("--site-packages")
            if python:
                cmd_list.extend(["--python", QuoteString(python)])
            cmd_list.extend(
                QuoteString(e)
                for e in ((extra_args or []) if not isinstance(extra_args, str) else [extra_args])
            )
            cmd_list.append(QuoteString(path))
            yield StringCommand(*cmd_list)
    else:
        if not exists:
            host.noop(f"venv does not exist at {path}")
        else:
            yield from files.directory._inner(f"{path}/{VENV}", present=False)  # noqa: SLF001
