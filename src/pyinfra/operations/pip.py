"""
Manage pip (python) packages. Compatible globally or inside
a virtualenv (virtual environment).
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Any, Literal

from pyinfra import host, logger
from pyinfra.api import QuoteString, StringCommand, operation
from pyinfra.facts.files import File
from pyinfra.facts.pip import PipPackages, PythonVersion

from . import files
from .util.packaging import PkgInfo, ensure_packages
from .util.venv import check_existing_venv


@operation()
def virtualenv(
    path: str,
    python: str | None = None,
    venv=False,
    site_packages=False,
    always_copy=False,
    present=True,
    on_mismatch: Literal["warn", "recreate", "ignore"] = "warn",
):
    """
    Add/remove Python virtualenvs.

    + python: python interpreter to use
    + venv: use standard venv module instead of virtualenv
    + site_packages: give access to the global site-packages
    + always_copy: always copy files rather than symlinking
    + present: whether the virtualenv should exist
    + on_mismatch: what to do with an existing virtualenv whose Python version differs from
      ``python``: ``warn`` keeps it and logs a warning, ``recreate`` deletes and recreates it,
      ``ignore`` skips the check

    Existing virtualenvs:
        A virtualenv whose interpreter can no longer be executed, typically because the Python
        it was created from was upgraded or removed, is deleted and created again. When
        ``python`` is given its major.minor version is also compared with the interpreter inside
        the virtualenv, and ``on_mismatch`` decides what happens when they differ. Set
        ``on_mismatch="ignore"`` to skip both checks.

    **Example:**

    .. code:: python

        from pyinfra.operations import pip
        pip.virtualenv(
            name="Create a virtualenv",
            path="/usr/local/bin/venv",
        )
    """

    yield from _virtualenv(
        path=path,
        python=python,
        venv=venv,
        site_packages=site_packages,
        always_copy=always_copy,
        present=present,
        on_mismatch=on_mismatch,
    )


def _virtualenv(
    path: str,
    python: str | None = None,
    venv: bool = False,
    site_packages: bool = False,
    always_copy: bool = False,
    present: bool = True,
    on_mismatch: Literal["warn", "recreate", "ignore"] = "warn",
) -> Generator[Any, None, bool]:
    """
    Yield the commands that make the virtualenv at ``path`` match the arguments, returning
    whether it is being (re)created. Shared by the virtualenv, venv and packages operations.
    """

    # Check for *contents* of a virtualenv, ie don't accept an empty directory
    # as a valid virtualenv but ensure the activate script exists.
    exists = host.get_fact(File, path=f"{path}/bin/activate")

    if not present:
        if exists:
            yield from files.directory._inner(path, present=False)
        else:
            host.noop(f"virtualenv {path} does not exist")
        return False

    if exists:
        recreate, reason = False, None
        if on_mismatch != "ignore":
            current = host.get_fact(PythonVersion, python=f"{path}/bin/python")
            wanted = None
            if current is not None and python is not None:
                wanted = host.get_fact(PythonVersion, python=python)
            recreate, reason = check_existing_venv(
                f"virtualenv {path}", current, wanted, python, on_mismatch
            )

        if not recreate:
            host.noop(f"virtualenv {path} exists" + (f" but {reason}" if reason else ""))
            return False

        logger.info(f"virtualenv {path}: {reason}, recreating")
        yield from files.directory._inner(path, present=False)

    command: list[str | QuoteString] = ["virtualenv"]

    if venv:
        command = [QuoteString(python) if python else "python", "-m", "venv"]

    if python and not venv:
        command.extend(["-p", QuoteString(python)])

    if site_packages:
        command.append("--system-site-packages")

    if always_copy and not venv:
        command.append("--always-copy")
    elif always_copy and venv:
        command.append("--copies")

    command.append(QuoteString(path))

    yield StringCommand(*command)
    return True


@operation()
def venv(
    path: str,
    python: str | None = None,
    site_packages=False,
    always_copy=False,
    present=True,
    on_mismatch: Literal["warn", "recreate", "ignore"] = "warn",
):
    """
    Add/remove Python virtualenvs.

    + python: python interpreter to use
    + site_packages: give access to the global site-packages
    + always_copy: always copy files rather than symlinking
    + present: whether the virtualenv should exist
    + on_mismatch: what to do with an existing virtualenv whose Python version differs from
      ``python``, see ``pip.virtualenv``

    **Example:**

    .. code:: python

        pip.venv(
            name="Create a virtualenv",
            path="/usr/local/bin/venv",
        )
    """

    yield from _virtualenv(
        venv=True,
        path=path,
        python=python,
        site_packages=site_packages,
        always_copy=always_copy,
        present=present,
        on_mismatch=on_mismatch,
    )


@operation()
def packages(
    packages: str | list[str] | None = None,
    present=True,
    latest=False,
    requirements: str | None = None,
    pip="pip",
    virtualenv: str | None = None,
    virtualenv_kwargs: dict | None = None,
    extra_install_args: str | None = None,
):
    """
    Install/remove/update pip packages.

    + packages: list of packages to ensure
    + present: whether the packages should be installed
    + latest: whether to upgrade packages without a specified version
    + requirements: location of requirements file to install/uninstall
    + pip: name or path of the pip directory to use
    + virtualenv: root directory of virtualenv to work in
    + virtualenv_kwargs: dictionary of arguments to pass to ``pip.virtualenv``
    + extra_install_args: additional arguments to the pip install command

    Virtualenv:
        This will be created if it does not exist already, and recreated when its Python no
        longer matches (see ``pip.virtualenv``). ``virtualenv_kwargs`` will be passed to
        ``pip.virtualenv`` which can be used to control how the env is created.

    Versions:
        Package versions can be pinned like pip: ``<pkg>==<version>``.

    **Example:**

    .. code:: python

        pip.packages(
            name="Install pyinfra into a virtualenv",
            packages=["pyinfra"],
            virtualenv="/usr/local/bin/venv",
        )
    """

    virtualenv_kwargs = virtualenv_kwargs or {}
    virtualenv_created = False

    # Ensure any virtualenv
    if virtualenv:
        virtualenv_created = yield from _virtualenv(virtualenv, **virtualenv_kwargs)

        # And update pip path
        virtualenv = virtualenv.rstrip("/")
        pip = StringCommand(QuoteString(virtualenv), "/bin/", pip, _separator="").get_raw_value()

    install_command_args = [pip, "install"]
    if extra_install_args:
        install_command_args.append(extra_install_args)
    install_command = " ".join(install_command_args)

    upgrade_command = f"{install_command} --upgrade"
    uninstall_command = " ".join([pip, "uninstall", "--yes"])

    # (un)Install requirements
    if requirements is not None:
        if present:
            yield StringCommand(
                upgrade_command if latest else install_command, "-r", QuoteString(requirements)
            )
        else:
            yield StringCommand(uninstall_command, "-r", QuoteString(requirements))

    # Handle passed in packages
    if packages:
        if isinstance(packages, str):
            packages = [packages]

        if virtualenv_created:
            # The fact would describe the virtualenv being replaced, the new one is empty
            current_packages = {}
        else:
            # PEP-0426 states that Python packages should be compared using lowercase, so
            # lowercase the current packages. PkgInfo.from_pep508 takes care of the package name
            current_packages = host.get_fact(PipPackages, pip=pip)
            current_packages = {pkg.lower(): versions for pkg, versions in current_packages.items()}

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
