# encoding: utf8
from __future__ import annotations

from typing_extensions import override

from pyinfra.api import FactBase

from .util.packaging import parse_packages

NPM_REGEX = r"^[└├]\─\─\s([a-zA-Z0-9\-]+)@([0-9\.]+)$"


class NpmPackages(FactBase):
    """
    Returns a dict of installed npm packages globally or in a given directory:

    .. code:: python

        {
            "package_name": ["version"],
        }
    """

    default = dict

    @override
    def requires_command(self, directory=None) -> str:
        return "npm"

    @override
    def command(self, directory=None):
        if directory:
            return ("! test -d {0} || (cd {0} && npm list -g --depth=0)").format(directory)
        return "npm list -g --depth=0"

    @override
    def process(self, output):
        return parse_packages(NPM_REGEX, output)


class NpmOutdatedPackages(FactBase):
    """
    Returns a dict of outdated npm packages and their latest available versions:

    .. code:: python

        {
            "package_name": "latest_version",
        }
    """

    default = dict
    use_default_on_error = True

    @override
    def requires_command(self, directory=None) -> str:
        return "npm"

    @override
    def command(self, directory=None):
        if directory:
            return (
                "! test -d {0} || (cd {0} && npm outdated -g --parseable 2>/dev/null || true)"
            ).format(directory)
        return "npm outdated -g --parseable 2>/dev/null || true"

    @override
    def process(self, output):
        packages: dict[str, str] = {}
        for line in output:
            # Format: path:current:wanted:latest:depended_by
            parts = line.split(":")
            if len(parts) >= 4:
                # The path part contains the package name at the end
                path = parts[0]
                latest = parts[3]
                # Extract package name from path (e.g. /usr/lib/node_modules/package)
                name = path.rsplit("/", 1)[-1] if "/" in path else path
                if name and latest:
                    packages[name] = latest
        return packages
