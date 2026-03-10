from __future__ import annotations

import re
import shlex

from typing_extensions import override

from pyinfra.api import FactBase

from .util.packaging import parse_packages

PACMAN_REGEX = r"^([0-9a-zA-Z\-_]+)\s([0-9\._+a-z\-:]+)"


class PacmanUnpackGroup(FactBase):
    """
    Returns a list of actual packages belonging to the provided package name,
    expanding groups or virtual packages.

    .. code:: python

        [
            "package_name",
        ]
    """

    @override
    def requires_command(self, *args, **kwargs) -> str:
        return "pacman"

    default = list

    @override
    def command(self, package):
        # Accept failure here (|| true) for invalid/unknown packages
        return 'pacman -S --print-format "%n" {0} || true'.format(shlex.quote(package))

    @override
    def process(self, output):
        return output


class PacmanPackages(FactBase):
    """
    Returns a dict of installed pacman packages:

    .. code:: python

        {
            "package_name": ["version"],
        }

    .. deprecated:: 3.x
        Use the enriched sub-facts :class:`PacmanUpgradeablePackages` and
        :class:`PacmanHeldPackages` together with
        :func:`~pyinfra.facts.util.packages.build_package_map` for richer
        package status information.
    """

    @override
    def command(self) -> str:
        return "pacman -Q"

    @override
    def requires_command(self, *args, **kwargs) -> str:
        return "pacman"

    default = dict

    @override
    def process(self, output):
        return parse_packages(PACMAN_REGEX, output)


class PacmanUpgradeablePackages(FactBase):
    """
    Returns a dict of upgradeable pacman packages:

    .. code:: python

        {
            "package_name": "available_version",
        }
    """

    @override
    def command(self) -> str:
        return "pacman -Qu"

    @override
    def requires_command(self, *args, **kwargs) -> str:
        return "pacman"

    default = dict
    use_default_on_error = True

    _regex = re.compile(r"^(\S+)\s+\S+\s+->\s+(\S+)$")

    @override
    def process(self, output):
        result: dict[str, str] = {}
        for line in output:
            match = self._regex.match(line)
            if match:
                result[match.group(1)] = match.group(2)
        return result


class PacmanHeldPackages(FactBase):
    """
    Returns a list of held (ignored) pacman packages from ``/etc/pacman.conf``.

    .. code:: python

        ["package_name", "another_package"]
    """

    @override
    def command(self) -> str:
        return "grep -E '^\\s*IgnorePkg' /etc/pacman.conf || true"

    @override
    def requires_command(self, *args, **kwargs) -> str:
        return "pacman"

    default = list

    _regex = re.compile(r"^\s*IgnorePkg\s*=\s*(.+?)(?:\s*#.*)?$")

    @override
    def process(self, output):
        result: list[str] = []
        for line in output:
            match = self._regex.match(line)
            if match:
                result.extend(match.group(1).split())
        return result
