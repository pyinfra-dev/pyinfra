from __future__ import annotations

import re

from typing_extensions import override

from pyinfra.api import FactBase


class UpstartStatus(FactBase):
    """
    Returns a dict of name -> status for upstart managed services.
    """

    @override
    def requires_command(self) -> str:
        return "initctl"

    regex = r"^([a-z\-]+) [a-z]+\/([a-z]+)"
    default = dict

    @override
    def command(self):
        return "initctl list"

    @override
    def process(self, output):
        services = {}

        for line in output:
            matches = re.match(self.regex, line)
            if matches:
                services[matches.group(1)] = matches.group(2) == "running"

        return services
