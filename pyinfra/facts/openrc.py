import re

from pyinfra.api import FactBase


class OpenrcStatus(FactBase):
    """
    Returns a dict of name -> status for OpenRC services for a given runlevel.
    """

    default = dict
    requires_command = "rc-status"
    regex = (
        r"\s+([a-zA-Z0-9\-_]+)"
        r"\s+\[\s+"
        r"([a-z]+)"
        r"(?:\s(?:[0-9]+\sday\(s\)\s)?"
        r"[0-9]+\:[0-9]+\:[0-9]+\s\([0-9]+\))?"
        r"\s+\]"
    )

    def command(self, runlevel="default"):
        return "rc-status {0}".format(runlevel)

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
    requires_command = "rc-update"

    def command(self, runlevel="default"):
        self.runlevel = runlevel
        return "rc-update show -v"

    def process(self, output):
        services = {}

        for line in output:
            name, levels = line.split("|", 1)
            name = name.strip()
            levels = levels.split()
            services[name] = self.runlevel in levels

        return services
