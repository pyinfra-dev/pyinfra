from __future__ import annotations

import re

from typing_extensions import override

from pyinfra.api import FactBase


class OpenrcStatus(FactBase):
    """
    Returns a dict of name -> status for OpenRC services for a given runlevel.
    """

    default = dict
    regex = (
        r"\s+([a-zA-Z0-9\-_]+)"
        r"\s+\[\s+"
        r"([a-z]+)"
        r"(?:\s(?:[0-9]+\sday\(s\)\s)?"
        r"[0-9]+\:[0-9]+\:[0-9]+\s\([0-9]+\))?"
        r"\s+\]"
    )

    @override
    def requires_command(self, runlevel="default") -> str:
        return "rc-status"

    @override
    def command(self, runlevel="default"):
        return "rc-status {0}".format(runlevel)

    @override
    def process(self, output):
        services = {}

        for line in output:
            matches = re.match(self.regex, line)
            if matches:
                services[matches.group(1)] = matches.group(2) == "started"

        return services


class OpenrcEnabled(FactBase):
    """
    Returns a dict of name -> whether enabled for OpenRC services for a given runlevel.
    """

    default = dict

    @override
    def requires_command(self, runlevel="default") -> str:
        return "rc-update"

    @override
    def command(self, runlevel="default"):
        self.runlevel = runlevel
        return "rc-update show -v"

    @override
    def process(self, output):
        services = {}

        for line in output:
            name, levels = line.split("|", 1)
            name = name.strip()
            levels = levels.split()
            services[name] = self.runlevel in levels

        return services
