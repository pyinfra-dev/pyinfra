from __future__ import annotations

import re

from typing_extensions import override

from pyinfra.api import FactBase

from .util.packaging import parse_packages

CHOCO_REGEX = r"^([a-zA-Z0-9\.\-\+\_]+)\s([0-9\.]+)$"


class ChocoPackages(FactBase):
    """
    Returns a dict of installed choco (Chocolatey) packages:

    .. code:: python

        {
            "package_name": ["version"],
        }
    """

    @override
    def command(self) -> str:
        return "choco list"

    shell_executable = "ps"

    default = dict

    @override
    def process(self, output):
        return parse_packages(CHOCO_REGEX, output)


class ChocoVersion(FactBase):
    """
    Returns the choco (Chocolatey) version.
    """

    @override
    def command(self) -> str:
        return "choco --version"

    @override
    def process(self, output):
        return "".join(output).replace("\n", "")


class ChocoOutdatedPackages(FactBase):
    """
    Returns a dict of outdated choco packages and their available versions:

    .. code:: python

        {
            "package_name": "available_version",
        }
    """

    shell_executable = "ps"
    default = dict
    use_default_on_error = True

    _regex = re.compile(r"^([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)$")

    @override
    def command(self) -> str:
        return "choco outdated -r 2>$null"

    @override
    def process(self, output):
        result: dict[str, str] = {}
        for line in output:
            match = self._regex.match(line)
            if match:
                name = match.group(1)
                available = match.group(3)
                pinned = match.group(4).strip().lower()
                if pinned != "true":
                    result[name] = available
        return result


class ChocoPinnedPackages(FactBase):
    """
    Returns a list of pinned choco packages:

    .. code:: python

        ["package_name", ...]
    """

    shell_executable = "ps"
    default = list
    use_default_on_error = True

    _regex = re.compile(r"^([^|]+)\|")

    @override
    def command(self) -> str:
        return "choco pin list -r 2>$null"

    @override
    def process(self, output):
        result: list[str] = []
        for line in output:
            match = self._regex.match(line)
            if match:
                result.append(match.group(1))
        return result
