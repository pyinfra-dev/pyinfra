from __future__ import annotations

import re

from typing_extensions import override

from pyinfra import logger
from pyinfra.api import FactBase

from .util.packaging import parse_packages

BREW_REGEX = r"^([^\s]+)\s([0-9\._+a-z\-]+)"


def new_cask_cli(version):
    """
    Returns true if brew is version 2.6.0 or later and thus has the new CLI for casks.
    i.e. we need to use brew list --cask instead of brew cask list
    See https://brew.sh/2020/12/01/homebrew-2.6.0/
    The version string returned by BrewVersion is a list of major, minor, patch version numbers
    """
    return (version[0] >= 3) or ((version[0] >= 2) and version[1] >= 6)


VERSION_MATCHER = re.compile(r"^Homebrew\s+(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+).*$")


def unknown_version():
    return [0, 0, 0]


class BrewVersion(FactBase):
    """
    Returns the version of brew installed as a semantic versioning tuple:

    .. code:: python

        [major, minor, patch]

    """

    @override
    def command(self) -> str:
        return "brew --version"

    @override
    def requires_command(self) -> str:
        return "brew"

    @override
    @staticmethod
    def default():
        return [0, 0, 0]

    @override
    def process(self, output):
        out = list(output)[0]
        m = VERSION_MATCHER.match(out)
        if m is not None:
            return [int(m.group(key)) for key in ["major", "minor", "patch"]]
        logger.warning("could not parse version string from brew: %s", out)
        return self.default()


class BrewPackages(FactBase):
    """
    Returns a dict of installed brew packages:

    .. code:: python

        {
            "package_name": ["version"],
        }
    """

    @override
    def command(self) -> str:
        return "brew list --versions"

    @override
    def requires_command(self) -> str:
        return "brew"

    default = dict

    @override
    def process(self, output):
        return parse_packages(BREW_REGEX, output)


class BrewCasks(BrewPackages):
    """
    Returns a dict of installed brew casks:

    .. code:: python

        {
            "package_name": ["version"],
        }
    """

    @override
    def command(self) -> str:
        return (
            r'if brew --version | grep -q -e "Homebrew\ +(1\.|2\.[0-5]).*" 1>/dev/null;'
            r"then brew cask list --versions; else brew list --cask --versions; fi"
        )

    @override
    def requires_command(self) -> str:
        return "brew"


class BrewTaps(FactBase):
    """
    Returns a list of brew taps.
    """

    @override
    def command(self) -> str:
        return "brew tap"

    @override
    def requires_command(self) -> str:
        return "brew"

    default = list

    @override
    def process(self, output):
        return output
