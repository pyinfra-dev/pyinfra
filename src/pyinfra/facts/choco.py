from __future__ import annotations

from typing_extensions import override

from pyinfra.api import FactBase

from .util.packaging import parse_packages

CHOCO_REGEX = r"^([a-zA-Z0-9\.\-\+\_]+)\s([0-9\.]+)$"


class ChocoPackages(FactBase):
    """
    Returns a dict of installed choco (Chocolatey) packages:

    .. code:: python

        {
            "package_name": ["version"],
        }
    """

    @override
    def command(self) -> str:
        return "choco list"

    shell_executable = "ps"

    default = dict

    @override
    def process(self, output):
        return parse_packages(CHOCO_REGEX, output)


class ChocoVersion(FactBase):
    """
    Returns the choco (Chocolatey) version.
    """

    @override
    def command(self) -> str:
        return "choco --version"

    @override
    def process(self, output):
        return "".join(output).replace("\n", "")
