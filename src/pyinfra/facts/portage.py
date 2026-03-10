from __future__ import annotations

import re

from typing_extensions import override

from pyinfra.api import FactBase

from .util.packaging import parse_packages

# Portage package atoms use category/name-version format.
# Package names can contain hyphens; versions always start with a digit.
# Non-greedy match on the name ensures we split at the first -digit boundary.
# Handles revisions like -r1: sys-devel/gcc-11.2.0-r1 -> ("sys-devel/gcc", "11.2.0-r1")
PORTAGE_REGEX = r"^(.+?)-(\d.*)$"


class PortagePackages(FactBase):
    """
    Returns a dict of installed Portage packages:

    .. code:: python

        {
            "sys-devel/gcc": ["11.2.0-r1"],
        }
    """

    @override
    def requires_command(self, *args, **kwargs) -> str:
        return "qlist"

    default = dict

    @override
    def command(self) -> str:
        return "qlist -Iv"

    @override
    def process(self, output):
        return parse_packages(PORTAGE_REGEX, output)


class PortageUpgradeablePackages(FactBase):
    """
    Returns a dict of upgradeable Portage packages and their available versions:

    .. code:: python

        {
            "sys-apps/portage": "2.3.99-r1",
        }
    """

    @override
    def requires_command(self, *args, **kwargs) -> str:
        return "emerge"

    default = dict
    use_default_on_error = True

    # Parse emerge pretend output for lines with U (update).
    # Example: [ebuild     U  ] sys-apps/portage-2.3.99-r1::gentoo [2.3.89::gentoo] ...
    _regex = re.compile(r"^\[ebuild\s+[^\]]*U[^\]]*\]\s+(.+?)-(\d[^:\s]*)::")

    @override
    def command(self) -> str:
        return "emerge -puDN @world 2>/dev/null || true"

    @override
    def process(self, output):
        result: dict[str, str] = {}
        for line in output:
            match = self._regex.match(line)
            if match:
                result[match.group(1)] = match.group(2)
        return result


class PortageMaskedPackages(FactBase):
    """
    Returns a list of masked package names from ``/etc/portage/package.mask``:

    .. code:: python

        ["sys-devel/gcc", "www-client/firefox"]
    """

    default = list
    use_default_on_error = True

    # Extract category/name from atoms like >=sys-devel/gcc-11.0 or sys-apps/systemd
    _atom_regex = re.compile(r"^[<>=~!]*(.+?)(?:-\d\S*)?$")

    @override
    def command(self) -> str:
        return "grep -rh '^[^#]' /etc/portage/package.mask 2>/dev/null || true"

    @override
    def process(self, output):
        result: list[str] = []
        seen: set[str] = set()
        for line in output:
            line = line.strip()
            if not line:
                continue
            match = self._atom_regex.match(line)
            if match:
                name = match.group(1)
                if "/" in name and name not in seen:
                    result.append(name)
                    seen.add(name)
        return result
