from __future__ import annotations

from typing_extensions import override

from pyinfra.api import FactBase

from .util.packaging import parse_packages


class XbpsPackages(FactBase):

    @staticmethod
    def has_updates():
        """
        Returns True if there are available updates for XBPS packages.
        """
        return host.run_shell_command("xbps-install -nu", hide=True)[0]
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
