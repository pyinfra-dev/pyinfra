from __future__ import annotations

import re

from typing_extensions import override

from pyinfra.api import FactBase

from .util import make_cat_files_command
from .util.packaging import parse_zypper_repositories


class ZypperUpgradeablePackages(FactBase):
    """
    Returns a dict of upgradeable zypper packages and their available versions:

    .. code:: python

        {
            "package_name": "available_version",
        }
    """

    default = dict
    use_default_on_error = True

    @override
    def command(self) -> str:
        return "zypper --non-interactive list-updates 2>/dev/null || true"

    @override
    def requires_command(self) -> str:
        return "zypper"

    @override
    def process(self, output):
        result: dict[str, str] = {}
        for line in output:
            line = line.strip()
            if not line or line.startswith("--") or line.startswith("S ") or "|" not in line:
                continue
            # zypper list-updates output format:
            # S | Repository | Name | Current Version | Available Version | Arch
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 5:
                name = parts[2]
                available_version = parts[4]
                # Skip header-like lines
                if name and name != "Name" and available_version:
                    result[name] = available_version
        return result


class ZypperHeldPackages(FactBase):
    """
    Returns a list of held (locked) zypper packages:

    .. code:: python

        [
            "package_name",
        ]
    """

    default = list
    use_default_on_error = True

    @override
    def command(self) -> str:
        return "zypper locks 2>/dev/null || true"

    @override
    def requires_command(self) -> str:
        return "zypper"

    @override
    def process(self, output):
        result: list[str] = []
        for line in output:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("--") or "|" not in line:
                continue
            # zypper locks output format:
            # # | Name | Type | Repository
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 2:
                name = parts[1]
                # Skip header lines
                if name and name != "Name":
                    # Strip any version constraints
                    name = re.sub(r"\s*[<>=].*$", "", name)
                    result.append(name)
        return result


class ZypperRepositories(FactBase):
    """
    Returns a list of installed zypper repositories:

    .. code:: python

        [
            {
                "repoid": "repo-oss",
                "name": "Main Repository",
                "enabled": "1",
                "autorefresh": "1",
                "baseurl": "http://download.opensuse.org/distribution/leap/$releasever/repo/oss/"
            },
        ]
    """

    @override
    def command(self) -> str:
        return make_cat_files_command(
            "/etc/zypp/repos.d/*.repo",
        )

    @override
    def requires_command(self) -> str:
        return "zypper"

    default = list

    @override
    def process(self, output):
        return parse_zypper_repositories(output)
