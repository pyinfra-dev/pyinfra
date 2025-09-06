from __future__ import annotations

import re

from typing_extensions import override

from pyinfra.api import FactBase


class SnapBaseFact(FactBase):
    abstract = True

    @override
    def requires_command(self, *args, **kwargs) -> str:
        return "snap"


class SnapPackage(SnapBaseFact):
    """
    Returns information for an installed snap package

    .. code:: python

        {
            "name": "lxd",
            "publisher": "Canonical✓",
            "snap-id": "J60k4JY0HppjwOjW8dZdYc8obXKxujRu",
            "channel": "4.0/stable",
            "version": "4.0.9"
        }
    """

    default = dict
    _regexes = {
        "name": "^name:[ ]+(.*)",
        "publisher": r"^publisher:[ ]+(.*)",
        "snap-id": r"^snap-id:[ ]+(.*)",
        "channel": r"^tracking:[ ]+([\w\d.-]+/[\w\d.-]+)[/]?.*$",
        "version": r"^installed:[ ]+([\w\d.-]+).*$",
    }

    @override
    def command(self, package):
        return f"snap info {package}"

    @override
    def process(self, output):
        data = {}
        for line in output:
            for regex_name, regex in self._regexes.items():
                matches = re.match(regex, line)
                if matches:
                    data[regex_name] = matches.group(1)

        return data


class SnapPackages(SnapBaseFact):
    """
    Returns a list of installed snap packages:

    .. code:: python

        [
            "core",
            "core18",
            "core20",
            "lxd",
            "snapd"
        ]
    """

    default = list

    @override
    def command(self) -> str:
        return "snap list"

    @override
    def process(self, output):
        # Discard header output line from snap list command
        # 'snap list' command example output lines:
        #    $ snap list
        #    Name              Version        Rev    Tracking         Publisher     Notes
        #    core              16-2.57.2      13886  latest/stable    canonical✓    core
        #    lxd               4.0.9          22753  4.0/stable/…     canonical✓    -
        #
        return [snap.split()[0] for snap in output[1:]]
