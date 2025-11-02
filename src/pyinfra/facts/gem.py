from __future__ import annotations

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
