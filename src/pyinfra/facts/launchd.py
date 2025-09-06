from __future__ import annotations

from typing_extensions import override

from pyinfra.api import FactBase


class LaunchdStatus(FactBase):
    """
    Returns a dict of name -> status for launchd managed services.
    """

    @override
    def command(self) -> str:
        return "launchctl list"

    @override
    def requires_command(self) -> str:
        return "launchctl"

    default = dict

    @override
    def process(self, output):
        services = {}

        for line in output:
            bits = line.split()

            if not bits or bits[0] == "PID":
                continue

            name = bits[2]
            status = False

            try:
                int(bits[0])
                status = True
            except ValueError:
                pass

            services[name] = status

        return services
