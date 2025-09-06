from __future__ import annotations

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
