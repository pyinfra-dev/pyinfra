from __future__ import annotations

from typing_extensions import override

from pyinfra.api import FactBase

from .util.packaging import parse_packages

# Source: https://superuser.com/a/1472405
# Modified to return version and release inside a single group and removed extra capturing groups
APK_REGEX = r"(.+)-([^-]+-r[^-]+) \S+ \{\S+\} \(.+?\)"


class ApkPackages(FactBase):
    """
    Returns a dict of installed apk packages:

    .. code:: python

        {
            "package_name": ["version"],
        }
    """

    @override
    def command(self) -> str:
        return "apk list --installed"

    @override
    def requires_command(self) -> str:
        return "apk"

    default = dict

    @override
    def process(self, output):
        return parse_packages(APK_REGEX, output)
