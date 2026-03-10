from __future__ import annotations

import re

from typing_extensions import override

from pyinfra.api import FactBase


class PaludisPackages(FactBase):
    """
    Returns a dict of installed Paludis packages:

    .. code:: python

        {
            "sys-apps/systemd": ["249"],
        }
    """

    @override
    def requires_command(self, *args, **kwargs) -> str:
        return "cave"

    default = dict

    _regex = re.compile(r"^(\S+)\s+(\S+)$")

    @override
    def command(self) -> str:
        return "cave print-ids -m '*/*::/' -f '%c/%p %v\\n'"

    @override
    def process(self, output):
        packages: dict[str, set[str]] = {}
        for line in output:
            match = self._regex.match(line.strip())
            if match:
                packages.setdefault(match.group(1), set()).add(match.group(2))
        return packages
