from __future__ import annotations

import re

from typing_extensions import override

from pyinfra.api import FactBase

from .util.packaging import parse_packages

# Source: https://superuser.com/a/1472405
# Modified to return version and release inside a single group and removed extra capturing groups
APK_REGEX = r"(.+)-([^-]+-r[^-]+) \S+ \{\S+\} \(.+?\)"

# Regex for `apk version -v -l '<'` output lines like:
#   vim-9.0.1-r0 < 9.0.2-r0
# Package names can contain hyphens, so the version starts after the last
# hyphen that is immediately followed by a digit.
APK_UPGRADEABLE_REGEX = re.compile(r"^(.+)-(\d\S*)\s+<\s+(\S+)$")


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


class ApkUpgradeablePackages(FactBase):
    """
    Returns a dict of packages with available upgrades:

    .. code:: python

        {
            "package_name": "available_version",
        }
    """

    @override
    def command(self) -> str:
        return "apk version -v -l '<'"

    @override
    def requires_command(self) -> str:
        return "apk"

    default = dict
    use_default_on_error = True

    @override
    def process(self, output):
        upgradeable: dict[str, str] = {}
        for line in output:
            match = APK_UPGRADEABLE_REGEX.match(line)
            if match:
                name = match.group(1)
                available_version = match.group(3)
                upgradeable[name] = available_version
        return upgradeable


class ApkHeldPackages(FactBase):
    """
    Returns a list of held (locked) apk packages.

    .. code:: python

        ["package_name", ...]
    """

    @override
    def command(self) -> str:
        return "apk lock --list 2>/dev/null || true"

    @override
    def requires_command(self) -> str:
        return "apk"

    default = list
    use_default_on_error = True

    @override
    def process(self, output):
        held: list[str] = []
        for line in output:
            line = line.strip()
            if line:
                held.append(line)
        return held
