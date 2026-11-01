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


class XbpsSelfUpdate(FactBase[list[str]]):
    """
    Returns the packages XBPS would update to update itself, empty if ``xbps``
    is up to date:

    .. code:: python

        ["xbps-triggers-0.128_1", "xbps-0.60.5_1"]

    XBPS refuses to install or update any other package until it has updated
    itself, failing with "The 'xbps' package must be updated". This reads the
    locally synced repository index, so it can only see a new ``xbps`` after
    ``xbps-install -S`` has run.
    """

    @override
    def requires_command(self) -> str:
        return "xbps-install"

    default = list

    # Dry run lines are "pkgver action arch repository installed_size download_size",
    # XBPS versions never contain a dash so this won't match eg xbps-triggers.
    xbps_regex = re.compile(r"^xbps-[^\s-]+_[0-9]+ update ")

    @override
    def command(self) -> str:
        return "xbps-install -n -u xbps"

    @override
    def process(self, output: list[str]) -> list[str]:
        if not any(self.xbps_regex.match(line) for line in output):
            return []
        return [line.split()[0] for line in output if line.strip()]
