from __future__ import annotations

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


class XbpsUpdates(FactBase):
        """
            Returns True if there are available updates for xbps packages, False otherwise.

                .. code:: python

                        True
                            """

    @override
    def requires_command(self) -> str:
                return "xbps-install"

    default = bool

    @override
    def command(self):
                return "xbps-install -nu 2>/dev/null | grep -q . && echo true || echo false"

    @override
    def process(self, output):
                return any(line.strip() == "true" for line in output)
