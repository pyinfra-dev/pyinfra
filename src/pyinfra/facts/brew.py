from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping, Sequence
from enum import Enum, unique
from typing import cast

from typing_extensions import override

from pyinfra import logger
from pyinfra.api import FactBase

from .util.packaging import parse_packages

BREW_REGEX = r"^([^\s]+)\s([0-9\._+a-z\-]+)"


@unique
class BrewItemKind(Enum):
    CASK = "casks"
    COMMAND = "commands"
    FORMULA = "formulae"
    TAP = "taps"


def _new_cask_cli(version: Sequence[int]) -> bool:
    """
    Returns true if brew is version 2.6.0 or later and thus has the new CLI for casks.
    i.e. we need to use brew list --cask instead of brew cask list
    See https://brew.sh/2020/12/01/homebrew-2.6.0/
    The version string returned by BrewVersion is a list of major, minor, patch version numbers
    """
    return (version[0] >= 3) or ((version[0] >= 2) and version[1] >= 6)


VERSION_MATCHER = re.compile(r"^Homebrew\s+(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+).*$")


BrewVersionType = list[int]


class BrewVersion(FactBase[Sequence[int]]):
    """
    Returns the version of brew installed as a semantic versioning list:

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
    def default() -> BrewVersionType:
        return [0, 0, 0]

    @override
    def process(self, output: Iterable[str]) -> BrewVersionType:
        if ((out := next(iter(output), None)) is not None) and (
            (m := VERSION_MATCHER.match(out)) is not None
        ):
            return [int(m.group(key)) for key in ["major", "minor", "patch"]]
        logger.warning(f"could not parse version string from brew: '{out}'")
        return self.default()


BrewPackingMapping = dict[str, set[str]]


class BrewPackages(FactBase[BrewPackingMapping]):
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
    def process(self, output: Iterable[str]) -> BrewPackingMapping:
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


BrewTapList = Iterable[str]


class BrewTaps(FactBase[BrewTapList]):
    """
    Returns a list of brew taps.

    .. code:: python
        {
            "@local": [
                "homebrew/cask",
                "homebrew/core",
                "homebrew/services",
            ]
        }
    """

    @override
    def command(self) -> str:
        return "brew tap"

    @override
    def requires_command(self) -> str:
        return "brew"

    default = list

    @override
    def process(self, output: Iterable[str]) -> BrewTapList:
        return output


BrewTrustMapping = Mapping[str, Sequence[str]]


class BrewTrusted(FactBase[BrewTrustMapping]):
    """
    Returns a dict with lists of the casks, commands, formulae and taps that have
    been marked as trusted

    .. code:: python
        {
            "@local": {
                "taps": [
                    "borgbackup/tap"
                ],
                "formulae": [],
                "casks": [],
                "commands": []
            }
        }
    """

    @override
    def command(self) -> str:
        return "brew trust --json=v1"

    @override
    def requires_command(self) -> str:
        return "brew"

    @override
    @staticmethod
    def default() -> BrewTrustMapping:
        return {kind.value: [] for kind in BrewItemKind.__members__.values()}

    @override
    def process(self, output: Iterable[str]) -> BrewTrustMapping:
        error = False
        body = "\n".join(s for s in output)
        try:
            result = cast("BrewTrustMapping", json.loads(body))
        except (json.JSONDecodeError, TypeError, RecursionError):
            error = True

        if error or not all(kind.value in result for kind in BrewItemKind.__members__.values()):
            logger.warning(f"unexpected output from brew trust: '{body}'")
            result = self.default()

        return result
