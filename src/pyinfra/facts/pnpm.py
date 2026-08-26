"""
Facts for pnpm, the fast, disk space efficient Node.js package manager.
See https://pnpm.io/

Facts taking a ``directory`` run pnpm inside it rather than under pnpm's ``--dir``,
so corepack - which resolves the pnpm version from the working directory - picks up
the project's ``packageManager`` pin.
"""

from __future__ import annotations

import json

from typing_extensions import override

from pyinfra import logger
from pyinfra.api import FactBase, QuoteString, StringCommand

from .util.packaging import PackageVersionDict

PNPM_CMD = "pnpm"

# Every dependency group ``pnpm list --json`` reports; all count as installed.
# ``unsavedDependencies`` is what is in ``node_modules`` but not the manifest.
DEPENDENCY_FIELDS = (
    "dependencies",
    "devDependencies",
    "optionalDependencies",
    "unsavedDependencies",
)

UP_TO_DATE_MARKER = "up_to_date"


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

        # A fact command that fails fails the host, so guard the directory - one that
        # isn't there yet simply has nothing installed. The subshell binds the guard,
        # as `A || B && C` parses as `(A || B) && C`.
        return StringCommand(
            "!",
            "test",
            "-d",
            QuoteString(directory),
            "||",
            "(cd",
            QuoteString(directory),
            "&&",
            PNPM_CMD,
            "list",
            "--depth=0",
            "--json)",
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
                    # Not every version is a semver: linked deps report ``link:<path>``.
                    version = package.get("version")
                    if version:
                        packages.setdefault(name, set()).add(version)

        return packages


class PnpmModulesUpToDate(FactBase[bool]):
    """
    Returns whether a project's ``node_modules`` was installed from the
    ``pnpm-lock.yaml`` now in the directory.

    pnpm keeps the lockfile it installed at ``node_modules/.pnpm/lock.yaml``, so
    the two matching means the packages on disk are the ones the lockfile asks
    for - though not that ``package.json`` agrees with the lockfile.
    """

    @override
    @staticmethod
    def default() -> bool:
        return False

    @override
    def command(self, directory: str) -> StringCommand:
        return StringCommand(
            "if",
            "cmp",
            "-s",
            QuoteString(f"{directory}/pnpm-lock.yaml"),
            QuoteString(f"{directory}/node_modules/.pnpm/lock.yaml"),
            ";",
            "then",
            f"echo {UP_TO_DATE_MARKER};",
            "else",
            "echo not_up_to_date;",
            "fi",
        )

    @override
    def process(self, output: list[str]) -> bool:
        return output[0].strip() == UP_TO_DATE_MARKER


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
