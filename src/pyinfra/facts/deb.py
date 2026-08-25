from __future__ import annotations

import re

from typing_extensions import override

from pyinfra.api import FactBase, QuoteString
from pyinfra.api.command import make_formatted_string_command

from .util.packaging import parse_packages

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
            "package_name": ["version"],
        }
    """

    @override
    def command(self) -> str:
        return "dpkg -l"

    @override
    def requires_command(self) -> str:
        return "dpkg"

    default = dict

    regex = (
        rf"^[i|h]i\s+({DEB_PACKAGE_NAME_REGEX}):?[a-zA-Z0-9]*\s+({DEB_PACKAGE_VERSION_REGEX}).+$"
    )

    @override
    def process(self, output):
        return parse_packages(self.regex, output)


class DebPackage(FactBase):
    """
    Returns information on a .deb archive or installed package.

    Package resolution depends on the remote current working directory and is
    therefore not idempotent:

    * Names that do not match the shell pattern ``*.deb`` query the installed
      package database.
    * Names that match ``*.deb`` inspect the archive only when that file exists
      in the current working directory. Otherwise they query the installed
      package database.

    Consequently, archive names such as ``package.deb.old`` and
    ``package.deb~`` cannot be queried as files. Older pyinfra versions tried
    to inspect any existing path as an archive instead.
    """

    _regexes = {
        "name": rf"^Package:\s+({DEB_PACKAGE_NAME_REGEX})$",
        "version": rf"^Version:\s+({DEB_PACKAGE_VERSION_REGEX})$",
    }

    @override
    def requires_command(self, package) -> str:
        return "dpkg"

    @override
    def command(self, package):
        return make_formatted_string_command(
            "test -f {0} && case {0} in *.deb) dpkg -I {0} ;; *) dpkg -s {0} 2>/dev/null || true ;; esac || dpkg -s {0} 2>/dev/null || true",
            QuoteString(package),
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
