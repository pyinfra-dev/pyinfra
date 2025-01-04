from __future__ import annotations

import re

from typing_extensions import TypedDict, override

from pyinfra.api import FactBase

from .gpg import GpgFactBase
from .util import make_cat_files_command


def noninteractive_apt(command: str, force=False):
    args = ["DEBIAN_FRONTEND=noninteractive apt-get -y"]

    if force:
        args.append("--force-yes")

    args.extend(
        (
            '-o Dpkg::Options::="--force-confdef"',
            '-o Dpkg::Options::="--force-confold"',
            command,
        ),
    )

    return " ".join(args)


APT_CHANGES_RE = re.compile(
    r"^(\d+) upgraded, (\d+) newly installed, (\d+) to remove and (\d+) not upgraded.$"
)


def parse_apt_repo(name):
    regex = r"^(deb(?:-src)?)(?:\s+\[([^\]]+)\])?\s+([^\s]+)\s+([^\s]+)\s+([a-z-\s\d]*)$"

    matches = re.match(regex, name)

    if not matches:
        return

    # Parse any options
    options = {}
    options_string = matches.group(2)
    if options_string:
        for option in options_string.split():
            key, value = option.split("=", 1)
            if "," in value:
                value = value.split(",")

            options[key] = value

    return {
        "options": options,
        "type": matches.group(1),
        "url": matches.group(3),
        "distribution": matches.group(4),
        "components": list(matches.group(5).split()),
    }


class AptSources(FactBase):
    """
    Returns a list of installed apt sources:

    .. code:: python

        [
            {
                "type": "deb",
                "url": "http://archive.ubuntu.org",
                "distribution": "trusty",
                "components", ["main", "multiverse"],
            },
        ]
    """

    @override
    def command(self) -> str:
        return make_cat_files_command(
            "/etc/apt/sources.list",
            "/etc/apt/sources.list.d/*.list",
        )

    @override
    def requires_command(self) -> str:
        return "apt"  # if apt installed, above should exist

    default = list

    @override
    def process(self, output):
        repos = []

        for line in output:
            repo = parse_apt_repo(line)
            if repo:
                repos.append(repo)

        return repos


class AptKeys(GpgFactBase):
    """
    Returns information on GPG keys apt has in its keychain:

    .. code:: python

        {
            "KEY-ID": {
                "length": 4096,
                "uid": "Oxygem <hello@oxygem.com>"
            },
        }
    """

    # This requires both apt-key *and* apt-key itself requires gpg
    @override
    def command(self) -> str:
        return "! command -v gpg || apt-key list --with-colons"

    @override
    def requires_command(self) -> str:
        return "apt-key"


class AptSimulationDict(TypedDict):
    upgraded: int
    newly_installed: int
    removed: int
    not_upgraded: int


class SimulateOperationWillChange(FactBase[AptSimulationDict]):
    """
    Simulate an 'apt-get' operation and try to detect if any changes would be performed.
    """

    @override
    def command(self, command: str) -> str:
        # LC_ALL=C: Ensure the output is in english, as we want to parse it
        return "LC_ALL=C " + noninteractive_apt(f"{command} --dry-run")

    @override
    def requires_command(self, command: str) -> str:
        return "apt-get"

    @override
    def process(self, output) -> AptSimulationDict:
        # We are looking for a line similar to
        # "3 upgraded, 0 newly installed, 0 to remove and 0 not upgraded."
        for line in output:
            result = APT_CHANGES_RE.match(line)
            if result is not None:
                return {
                    "upgraded": int(result[1]),
                    "newly_installed": int(result[2]),
                    "removed": int(result[3]),
                    "not_upgraded": int(result[4]),
                }

        # We did not find the line we expected:
        raise Exception("Did not find proposed changes in output")
