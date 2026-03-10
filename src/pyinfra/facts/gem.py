from __future__ import annotations

import re

from typing_extensions import override

from pyinfra.api import FactBase

from .util.packaging import parse_packages

GEM_REGEX = r"^([a-zA-Z0-9\-\+\_]+)\s\(([0-9\.]+)\)$"


class GemPackages(FactBase):
    """
    Returns a dict of installed gem packages:

    .. code:: python

        {
            'package_name': ['version'],
        }
    """

    @override
    def command(self) -> str:
        return "gem list --local"

    @override
    def requires_command(self) -> str:
        return "gem"

    default = dict

    @override
    def process(self, output):
        return parse_packages(GEM_REGEX, output)


class GemOutdatedPackages(FactBase):
    """
    Returns a dict of outdated gem packages and their latest available versions:

    .. code:: python

        {
            "package_name": "latest_version",
        }
    """

    default = dict
    use_default_on_error = True

    @override
    def command(self) -> str:
        return "gem outdated 2>/dev/null || true"

    @override
    def requires_command(self) -> str:
        return "gem"

    @override
    def process(self, output):
        packages: dict[str, str] = {}
        for line in output:
            # Format: package_name (installed < available)
            match = re.match(r"^(\S+)\s+\(\S+\s+<\s+(\S+)\)$", line)
            if match:
                packages[match.group(1)] = match.group(2)
        return packages
