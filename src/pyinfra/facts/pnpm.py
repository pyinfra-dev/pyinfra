"""
Facts for pnpm, the fast, disk space efficient Node.js package manager.
See https://pnpm.io/
"""

from __future__ import annotations

import json

from typing_extensions import override

from pyinfra import logger
from pyinfra.api import FactBase, QuoteString, StringCommand

from .util.packaging import PackageVersionDict

PNPM_CMD = "pnpm"

# The dependency groups ``pnpm list --json`` reports, all of which count as
# installed packages. Anything in ``node_modules`` but missing from the
# manifest is reported under ``unsavedDependencies``.
DEPENDENCY_FIELDS = (
    "dependencies",
    "devDependencies",
    "optionalDependencies",
    "unsavedDependencies",
)


class PnpmPackages(FactBase[PackageVersionDict]):
    """
    Returns a dict of installed pnpm packages, globally or in a given directory:

    .. code:: python

        {
            "package_name": {"version"},
        }
    """

    @override
    @staticmethod
    def default() -> PackageVersionDict:
        return {}

    @override
    def requires_command(self, directory: str | None = None) -> str:
        return PNPM_CMD

    @override
    def command(self, directory: str | None = None) -> StringCommand:
        if directory is None:
            return StringCommand(PNPM_CMD, "--global", "list", "--depth=0", "--json")

        # pnpm fails on a directory that doesn't exist, so guard on it - no
        # directory means no packages installed there (yet).
        return StringCommand(
            "!",
            "test",
            "-d",
            QuoteString(directory),
            "||",
            PNPM_CMD,
            "--dir",
            QuoteString(directory),
            "list",
            "--depth=0",
            "--json",
        )

    @override
    def process(self, output: list[str]) -> PackageVersionDict:
        try:
            projects = json.loads("\n".join(output))
        except json.JSONDecodeError:
            logger.warning(f"{self.name}: could not parse pnpm JSON output: {output}")
            return {}

        if not isinstance(projects, list):
            logger.warning(f"{self.name}: unexpected pnpm JSON output: {output}")
            return {}

        packages: PackageVersionDict = {}

        for project in projects:
            for field in DEPENDENCY_FIELDS:
                for name, package in project.get(field, {}).items():
                    # Linked & unmet dependencies have no version to compare.
                    version = package.get("version")
                    if version:
                        packages.setdefault(name, set()).add(version)

        return packages


class PnpmVersion(FactBase[str]):
    """
    Returns the version of pnpm installed:

    .. code:: python

        "10.15.1"
    """

    @override
    @staticmethod
    def default() -> str:
        return ""

    @override
    def requires_command(self) -> str:
        return PNPM_CMD

    @override
    def command(self) -> str:
        return f"{PNPM_CMD} --version"

    @override
    def process(self, output: list[str]) -> str:
        return "".join(output).strip()
