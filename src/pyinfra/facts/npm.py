# encoding: utf8
from __future__ import annotations

from typing_extensions import override

from pyinfra.api import FactBase

from .util.packaging import parse_packages

NPM_REGEX = r"^[└├]\─\─\s([a-zA-Z0-9\-]+)@([0-9\.]+)$"


class NpmPackages(FactBase):
    """
    Returns a dict of installed npm packages globally or in a given directory:

    .. code:: python

        {
            "package_name": ["version"],
        }
    """

    default = dict

    @override
    def requires_command(self, directory=None) -> str:
        return "npm"

    @override
    def command(self, directory=None):
        if directory:
            return ("cd {0} && npm list -g --depth=0").format(directory)
        return "npm list -g --depth=0"

    @override
    def process(self, output):
        return parse_packages(NPM_REGEX, output)
