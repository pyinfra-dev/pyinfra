from __future__ import annotations

import re

from typing_extensions import override

from pyinfra.api import FactBase

from .util.packaging import parse_packages


class XbpsPackages(FactBase):
    """
    Returns a dict of installed XBPS packages:

    .. code:: python

        {
            "package_name": ["version"],
        }
    """

    @override
    def requires_command(self) -> str:
        return "xbps-query"

    default = dict

    regex = r"^.. ([a-zA-Z0-9_\-\+\.]+)\-([0-9a-z\.]+_[0-9]+)"

    @override
    def command(self):
        return "xbps-query -l"

    @override
    def process(self, output):
        return parse_packages(self.regex, output)


class XbpsUpgradeablePackages(FactBase):
    """
    Returns a dict of upgradeable XBPS packages and their available versions:

    .. code:: python

        {
            "package_name": "available_version",
        }
    """

    @override
    def requires_command(self, *args, **kwargs) -> str:
        return "xbps-install"

    default = dict
    use_default_on_error = True

    _regex = re.compile(r"^([a-zA-Z0-9_\-\+\.]+)-([0-9a-z\.]+_[0-9]+)\s+")

    @override
    def command(self) -> str:
        return "xbps-install -Mun 2>/dev/null || true"

    @override
    def process(self, output):
        result: dict[str, str] = {}
        for line in output:
            match = self._regex.match(line)
            if match:
                result[match.group(1)] = match.group(2)
        return result
