from __future__ import annotations

import re

from typing_extensions import override

from pyinfra.api import FactBase

from .util.packaging import parse_packages

PKGIN_REGEX = r"^([a-zA-Z\-0-9]+)-([0-9\.]+\-?[a-z0-9]*)\s"


class PkginPackages(FactBase):
    """
    Returns a dict of installed pkgin packages:

    .. code:: python

        {
            "package_name": ["version"],
        }
    """

    @override
    def command(self) -> str:
        return "pkgin list"

    @override
    def requires_command(self) -> str:
        return "pkgin"

    default = dict

    @override
    def process(self, output):
        return parse_packages(PKGIN_REGEX, output)


class PkginUpgradeablePackages(FactBase):
    """
    Returns a dict of upgradeable pkgin packages and their available versions:

    .. code:: python

        {
            "package_name": "available_version",
        }
    """

    @override
    def requires_command(self, *args, **kwargs) -> str:
        return "pkgin"

    default = dict
    use_default_on_error = True

    _regex = re.compile(r"^([a-zA-Z\-0-9]+)-([0-9\.]+\-?[a-z0-9]*)\s")

    @override
    def command(self) -> str:
        return "pkgin upgrade -n 2>/dev/null || true"

    @override
    def process(self, output):
        result: dict[str, str] = {}
        for line in output:
            match = self._regex.match(line)
            if match:
                result[match.group(1)] = match.group(2)
        return result
