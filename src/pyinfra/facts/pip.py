from __future__ import annotations

import re

from typing_extensions import override

from pyinfra.api import FactBase

from .util.packaging import parse_packages

PIP_REGEX = r"^([a-zA-Z0-9_\-\+\.]+)==([0-9\.]+[a-z0-9\-]*)$"


class PipPackages(FactBase):
    """
    Returns a dict of installed pip packages:

    .. code:: python

        {
            "package_name": ["version"],
        }
    """

    default = dict
    pip_command = "pip"

    @override
    def requires_command(self, pip=None):
        return pip or self.pip_command

    @override
    def command(self, pip=None):
        pip = pip or self.pip_command
        return "{0} freeze --all".format(pip)

    @override
    def process(self, output):
        return parse_packages(PIP_REGEX, output)


class Pip3Packages(PipPackages):
    pip_command = "pip3"


class PipOutdatedPackages(FactBase):
    """
    Returns a dict of outdated pip packages and their latest available versions:

    .. code:: python

        {
            "package_name": "latest_version",
        }
    """

    default = dict
    use_default_on_error = True
    pip_command = "pip"

    @override
    def requires_command(self, pip=None):
        return pip or self.pip_command

    @override
    def command(self, pip=None):
        pip = pip or self.pip_command
        return "{0} list --outdated --format=columns 2>/dev/null || true".format(pip)

    @override
    def process(self, output):
        packages: dict[str, str] = {}
        for line in output:
            # Skip header lines (Package/Version/Latest/Type and separator ----)
            if line.startswith("Package") or line.startswith("---"):
                continue
            match = re.match(r"^(\S+)\s+\S+\s+(\S+)\s+\S+$", line)
            if match:
                packages[match.group(1)] = match.group(2)
        return packages
