from __future__ import annotations

import re

from typing_extensions import override

from pyinfra.api import FactBase

from .util.packaging import parse_packages


class PkgPackages(FactBase):
    """
    Returns a dict of installed pkg packages:

    .. code:: python

        {
            "package_name": ["version"],
        }
    """

    regex = r"^([a-zA-Z0-9_\-\+]+)\-([0-9a-z\.]+)"
    default = dict

    @override
    def command(self) -> str:
        return "pkg info || pkg_info || true"

    @override
    def process(self, output):
        return parse_packages(self.regex, output)


class PkgUpgradeablePackages(FactBase):
    """
    Returns a dict of upgradeable FreeBSD pkg packages and their available versions:

    .. code:: python

        {
            "package_name": "available_version",
        }
    """

    @override
    def requires_command(self, *args, **kwargs) -> str:
        return "pkg"

    default = dict
    use_default_on_error = True

    _regex = re.compile(
        r"^([a-zA-Z0-9_\-\+\.]+)-[^\s]+\s+[<>]\s+needs updating \(remote has ([^\)]+)\)"
    )

    @override
    def command(self) -> str:
        return "pkg version -vRL= 2>/dev/null || true"

    @override
    def process(self, output):
        result: dict[str, str] = {}
        for line in output:
            match = self._regex.match(line)
            if match:
                result[match.group(1)] = match.group(2)
        return result


class PkgLockedPackages(FactBase):
    """
    Returns a list of locked FreeBSD pkg packages:

    .. code:: python

        ["package_name", ...]
    """

    @override
    def requires_command(self, *args, **kwargs) -> str:
        return "pkg"

    default = list
    use_default_on_error = True

    _regex = re.compile(r"^([a-zA-Z0-9_\-\+\.]+)-[^\s:]+:\s+locked")

    @override
    def command(self) -> str:
        return "pkg lock -l 2>/dev/null || true"

    @override
    def process(self, output):
        result: list[str] = []
        for line in output:
            match = self._regex.match(line)
            if match:
                result.append(match.group(1))
        return result
