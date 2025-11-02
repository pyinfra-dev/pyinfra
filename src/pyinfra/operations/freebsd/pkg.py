"""
Manage FreeBSD packages.
"""

from __future__ import annotations

from typing_extensions import List, Optional, Union

from pyinfra import host
from pyinfra.api import QuoteString, StringCommand, operation
from pyinfra.facts.freebsd import PkgPackage


@operation()
def update(jail: Optional[str] = None, force: bool = False, reponame: Optional[str] = None):
    """
    Update the local catalogues of the enabled package repositories.

    + jail: See ``-j`` in ``pkg(8)``.
    + force: See ``-f`` in ``pkg-update(8)``.
    + reponame: See ``-r`` in ``pkg-update(8)``

    **Examples:**

    .. code:: python

        # host
        pkg.update()

        # jail
        pkg.update(
            jail="nginx"
        )
    """

    args: List[Union[str, "QuoteString"]] = []

    args.append("pkg")

    if jail is not None:
        args.extend(["-j", QuoteString(jail)])

    args.extend(["update"])

    if force:
        args.append("-f")

    if reponame is not None:
        args.extend(["-r", QuoteString(reponame)])

    yield StringCommand(*args)


@operation()
def upgrade(jail: Optional[str] = None, force: bool = False, reponame: Optional[str] = None):
    """
    Perform upgrades of package software distributions.

    + jail: See ``-j`` in ``pkg(8)``.
    + force: See ``-f`` in ``pkg-upgrade(8)``.
    + reponame: See ``-r`` in ``pkg-upgrade(8)``.

    **Examples:**

    .. code:: python

        # host
        pkg.upgrade()

        # jail
        pkg.upgrade(
            jail="nginx"
        )
    """

    args: List[Union[str, "QuoteString"]] = []

    args.append("pkg")

    if jail is not None:
        args.extend(["-j", QuoteString(jail)])

    args.extend(["upgrade", "-y"])

    if force:
        args.append("-f")

    if reponame is not None:
        args.extend(["-r", QuoteString(reponame)])

    yield StringCommand(*args)


@operation()
def install(package: str, jail: Optional[str] = None, reponame: Optional[str] = None):
    """
    Install packages from remote packages repositories or local archives.

    + package: Package to install.
    + jail: See ``-j`` in ``pkg(8)``.
    + reponame: See ``-r`` in ``pkg-install(8)``.

    **Example:**

    .. code:: python

        pkg.install("nginx")
    """

    if host.get_fact(PkgPackage, package=package, jail=jail):
        host.noop(f"Package '{package}' already installed")
        return

    args: List[Union[str, "QuoteString"]] = []

    args.append("pkg")

    if jail is not None:
        args.extend(["-j", QuoteString(jail)])

    args.extend(["install", "-y"])

    if reponame is not None:
        args.extend(["-r", QuoteString(reponame)])

    args.extend(["--", QuoteString(package)])

    yield StringCommand(*args)


@operation()
def remove(package: str, jail: Optional[str] = None):
    """
    Deletes packages from the database and the system.

    + package: Package to remove.
    + jail: See ``-j`` in ``pkg(8)``.

    **Example:**

    .. code:: python

        pkg.remove("nginx")
    """

    if not host.get_fact(PkgPackage, package=package, jail=jail):
        host.noop(f"Package '{package}' cannot be found")
        return

    args: List[Union[str, "QuoteString"]] = []

    args.append("pkg")

    if jail is not None:
        args.extend(["-j", QuoteString(jail)])

    args.extend(["remove", "-y"])

    args.extend(["--", QuoteString(package)])

    yield StringCommand(*args)


@operation()
def autoremove(jail: Optional[str] = None):
    """
    Remove orphan packages.

    + jail: See ``-j`` in ``pkg(8)``.

    **Example:**

    .. code:: python

        pkg.autoremove()
    """

    args: List[Union[str, "QuoteString"]] = []

    args.append("pkg")

    if jail is not None:
        args.extend(["-j", QuoteString(jail)])

    args.extend(["autoremove", "-y"])

    yield StringCommand(*args)


@operation()
def clean(all_pkg: bool = False, jail: Optional[str] = None):
    """
    Clean the local cache of fetched remote packages.

    + all_pkg: See ``-a`` in ``pkg-clean(8)``.
    + jail: See ``-j`` in ``pkg(8)``.

    **Example:**

    .. code:: python

        pkg.clean(
            all_pkg=True
        )
    """

    args: List[Union[str, "QuoteString"]] = []

    args.append("pkg")

    if jail is not None:
        args.extend(["-j", QuoteString(jail)])

    args.extend(["clean", "-y"])

    if all_pkg:
        args.append("-a")

    yield StringCommand(*args)
