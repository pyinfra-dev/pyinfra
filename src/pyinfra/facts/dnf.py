from __future__ import annotations

from typing_extensions import override

from pyinfra.api import FactBase

from .util import make_cat_files_command
from .util.packaging import parse_yum_repositories


class DnfRepositories(FactBase):
    """
    Returns a list of installed dnf repositories:

    .. code:: python

        [
            {
                "repoid": "baseos",
                "name": "AlmaLinux $releasever - BaseOS",
                "mirrorlist": "https://mirrors.almalinux.org/mirrorlist/$releasever/baseos",
                "enabled": "1",
                "gpgcheck": "1",
                "countme": "1",
                "gpgkey": "file:///etc/pki/rpm-gpg/RPM-GPG-KEY-AlmaLinux-9",
                "metadata_expire": "86400",
                "enabled_metadata": "1"
            },
        ]
    """

    @override
    def command(self) -> str:
        return make_cat_files_command(
            "/etc/dnf.conf",
            "/etc/dnf.repos.d/*.repo",
            "/etc/yum.repos.d/*.repo",
        )

    @override
    def requires_command(self) -> str:
        return "dnf"

    default = list

    @override
    def process(self, output):
        return parse_yum_repositories(output)


class DnfEnabledModules(FactBase):
    """
    Returns a dict mapping enabled dnf module names to their enabled stream:

    .. code:: python

        {
            "postgresql": "16",
            "nodejs": "20",
        }
    """

    @override
    def command(self) -> str:
        return "dnf module list --enabled"

    @override
    def requires_command(self) -> str:
        return "dnf"

    default = dict

    @override
    def process(self, output):
        result: dict[str, str] = {}
        for line in output:
            # Every data row from `--enabled` carries the [e] flag; this is the
            # cheapest way to skip repo-section headers, the column header, the
            # Hint legend and any blank lines.
            if "[e]" not in line:
                continue
            tokens = line.split()
            if len(tokens) < 2:
                continue
            name, stream = tokens[0], tokens[1]
            if name == "Name":
                continue
            result[name] = stream
        return result


class DnfDisabledModules(FactBase):
    """
    Returns a sorted list of dnf module names that have been explicitly disabled:

    .. code:: python

        ["ruby", "php"]
    """

    @override
    def command(self) -> str:
        return "dnf module list --disabled"

    @override
    def requires_command(self) -> str:
        return "dnf"

    default = list

    @override
    def process(self, output):
        seen: set[str] = set()
        for line in output:
            if "[x]" not in line:
                continue
            tokens = line.split()
            if not tokens:
                continue
            name = tokens[0]
            if name == "Name":
                continue
            seen.add(name)
        return sorted(seen)
