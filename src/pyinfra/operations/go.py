"""
Manage Go (Golang) binary packages installed via ``go install``.
"""

from __future__ import annotations

import re

from pyinfra import host
from pyinfra.api import QuoteString, StringCommand, operation
from pyinfra.facts.go import GoPackages


def _binary_name(pkg_path: str) -> str:
    """
    Return the basename of the binary produced by ``go install <pkg_path>``.

    Under Go's Semantic Import Versioning, modules at major version v2+ carry
    a ``/v<N>`` suffix on their import path that is not part of the binary
    name — e.g. ``github.com/foo/bar/v2`` installs a binary named ``bar``.

    Note: two distinct import paths can map to the same binary name (e.g.
    ``a/b/cmd/tool`` and ``x/y/cmd/tool``), mirroring how ``go install`` itself
    would clobber one binary with the other; on removal this means ``rm -f``
    cannot tell them apart.
    """
    parts = pkg_path.split("/")
    if len(parts) >= 2 and re.fullmatch(r"v\d+", parts[-1]):
        return parts[-2]
    return parts[-1]


@operation()
def packages(
    packages: str | list[str] | None = None,
    present: bool = True,
    latest: bool = False,
):
    """
    Add/remove/update Go binary packages installed via ``go install``.

    + packages: list of packages to ensure
    + present: whether the packages should be installed
    + latest: whether to upgrade packages without a specified version

    Note:
        ``latest=True`` is not idempotent offline: without a version to compare
        against, an installed unversioned package always re-runs ``go install``
        and reports as changed every run (same as ``pip.packages`` with latest).

    Versions:
        Package versions can be pinned like go: ``<pkg>@<version>``. Packages
        without a pinned version (or with the special ``@latest`` suffix) are
        installed at the latest available version.

    **Example:**

    .. code:: python

        from pyinfra.operations import go
        # Note: Assumes that 'go' is installed.
        go.packages(
            name="Install staticcheck",
            packages=["honnef.co/go/tools/cmd/staticcheck"],
        )
    """

    if packages is None:
        return
    if isinstance(packages, str):
        packages = [packages]

    current_packages = host.get_fact(GoPackages)

    to_install: list[str] = []
    to_upgrade: list[str] = []
    to_remove: list[str] = []

    for pkg in packages:
        name, _, version = pkg.partition("@")
        # `@latest` is the install-time pseudo-version, not a real installed
        # version, so treat it the same as "no version specified" for matching.
        unversioned = version == "" or version == "latest"

        installed_versions = current_packages.get(name) or []

        if present:
            if unversioned:
                if not installed_versions:
                    to_install.append(f"{name}@latest")
                elif latest:
                    to_upgrade.append(f"{name}@latest")
                else:
                    host.noop(
                        f"package {name} is installed ({','.join(sorted(installed_versions))})"
                    )
            elif version not in installed_versions:
                to_install.append(f"{name}@{version}")
            else:
                host.noop(f"package {name}@{version} is installed")
        else:
            if installed_versions:
                to_remove.append(name)
            else:
                host.noop(f"package {name} is not installed")

    if to_install:
        yield StringCommand("go install", *(QuoteString(p) for p in to_install))

    if to_upgrade:
        yield StringCommand("go install", *(QuoteString(p) for p in to_upgrade))

    if to_remove:
        yield StringCommand(
            "BINDIR=$(go env GOBIN);",
            '[ -z "$BINDIR" ] && BINDIR="$(go env GOPATH)/bin";',
            "rm -f",
            *(
                StringCommand('"$BINDIR"/', QuoteString(_binary_name(name)), _separator="")
                for name in to_remove
            ),
        )
