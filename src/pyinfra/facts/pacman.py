from __future__ import annotations

from typing_extensions import override

from pyinfra.api import FactBase, QuoteString
from pyinfra.api.command import make_formatted_string_command

from .util.packaging import parse_packages

PACMAN_REGEX = r"^([0-9a-zA-Z\-_]+)\s([0-9\._+a-z\-:]+)"


class PacmanUnpackGroup(FactBase):
    """
    Returns a list of actual packages belonging to the provided package name,
    expanding groups or virtual packages.

    .. code:: python

        [
            "package_name",
        ]
    """

    @override
    def requires_command(self, *args, **kwargs) -> str:
        return "pacman"

    default = list

    @override
    def command(self, package):
        # Accept failure here (|| true) for invalid/unknown packages
        return make_formatted_string_command(
            'pacman -S --print-format "%n" {0} || true', QuoteString(package)
        )

    @override
    def process(self, output):
        return output


class PacmanPackages(FactBase):
    """
    Returns a dict of installed pacman packages:

    .. code:: python

        {
            "package_name": ["version"],
        }
    """

    @override
    def command(self) -> str:
        return "pacman -Q"

    @override
    def requires_command(self, *args, **kwargs) -> str:
        return "pacman"

    default = dict

    @override
    def process(self, output):
        return parse_packages(PACMAN_REGEX, output)
