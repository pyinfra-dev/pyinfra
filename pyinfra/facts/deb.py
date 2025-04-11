from __future__ import annotations

import re
import shlex

from typing_extensions import override

from pyinfra.api import FactBase

DEB_PACKAGE_NAME_REGEX = r"[a-zA-Z0-9\+\-\.]+"
DEB_PACKAGE_VERSION_REGEX = r"[a-zA-Z0-9:~\.\-\+]+"


class DebArch(FactBase):
    """
    Returns the architecture string used in apt repository sources, eg ``amd64``.
    """

    @override
    def command(self) -> str:
        return "dpkg --print-architecture"

    @override
    def requires_command(self) -> str:
        return "dpkg"


class DebPackages(FactBase):
    """
    Returns a dict of installed dpkg packages:

    .. code:: python

        {
            "package_name": {
                "desired": "Install",
                "status": "Installed",
                "version": "version",
                "architecture": "architecture",
                "description": "description",
            }
        }
    """

    @override
    def command(self) -> str:
        return "dpkg -l"

    @override
    def requires_command(self) -> str:
        return "dpkg"

    default = dict

    regex = r"^([uirph]{1})([nicuhwt]{1})\s+([\w\-\.]+)\s+([\w\-\+\.:~]+)\s+(\w+)\s+(.+)$"

    @override
    def process(self, output):
        packages = {}

        # Mapping of single-letter codes to their full meanings
        desired_map = {
            "u": "Unknown",
            "i": "Install",
            "r": "Remove",
            "p": "Purge",
            "h": "Hold",
        }

        status_map = {
            "n": "Not-installed",
            "i": "Installed",
            "c": "Config-files",
            "u": "Unpacked",
            "h": "Half-installed",
            "w": "Trigger-awaited",
            "t": "Trigger-pending",
        }

        for line in output:
            matches = re.match(self.regex, line)
            if matches:
                desired_code = matches.group(1)  # Desired action (u,i,r,p,h)
                status_code = matches.group(2)  # Current status (n,i,c,u,h,w,t)
                name = matches.group(3)  # Package name
                version = matches.group(4)  # Version
                arch = matches.group(5)  # Architecture
                description = matches.group(6).strip()  # Description

                packages[name] = {
                    "desired": desired_map.get(desired_code, "Unknown"),
                    "status": status_map.get(status_code, "Unknown"),
                    "version": version,
                    "architecture": arch,
                    "description": description,
                }
        return packages


class DebPackage(FactBase):
    """
    Returns information on a .deb archive or installed package.
    """

    _regexes = {
        "name": r"^Package:\s+({0})$".format(DEB_PACKAGE_NAME_REGEX),
        "version": r"^Version:\s+({0})$".format(DEB_PACKAGE_VERSION_REGEX),
        "architecture": r"^Architecture:\s+(.*)$",
        "description": r"^Description:\s+(.*)$",
        "status": r"^Status:\s+(.*)$",
    }

    @override
    def requires_command(self, package) -> str:
        return "dpkg"

    @override
    def command(self, package):
        return "! test -e {0} && (dpkg -s {0} 2>/dev/null || true) || dpkg -I {0}".format(
            shlex.quote(package)
        )

    @override
    def process(self, output):
        data = {}

        for line in output:
            line = line.strip()
            for key, regex in self._regexes.items():
                matches = re.match(regex, line)
                if matches:
                    value = matches.group(1)
                    data[key] = value
                    break

        return data
