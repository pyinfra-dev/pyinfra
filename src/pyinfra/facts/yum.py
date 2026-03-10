from __future__ import annotations

import re

from typing_extensions import override

from pyinfra.api import FactBase

from .util import make_cat_files_command
from .util.packaging import parse_yum_repositories


class YumUpgradeablePackages(FactBase):
    """
    Returns a dict of upgradeable yum packages and their available versions:

    .. code:: python

        {
            "package_name": "available_version",
        }
    """

    default = dict
    use_default_on_error = True

    @override
    def command(self) -> str:
        return "yum check-update -q 2>/dev/null; true"

    @override
    def requires_command(self) -> str:
        return "yum"

    @override
    def process(self, output):
        result: dict[str, str] = {}
        for line in output:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 2:
                # Package name may have .arch suffix (e.g., vim.x86_64)
                name = re.sub(r"\.\w+$", "", parts[0])
                version = parts[1]
                result[name] = version
        return result


class YumHeldPackages(FactBase):
    """
    Returns a list of held (version-locked) yum packages:

    .. code:: python

        [
            "package_name",
        ]
    """

    default = list
    use_default_on_error = True

    @override
    def command(self) -> str:
        return "yum versionlock list 2>/dev/null || true"

    @override
    def requires_command(self) -> str:
        return "yum"

    @override
    def process(self, output):
        result: list[str] = []
        for line in output:
            line = line.strip()
            if not line or line.startswith("Last metadata") or line.startswith("Loaded plugins"):
                continue
            # versionlock lines can be like "0:vim-enhanced-8.0.1763-1.el7.*"
            # or just "package-name-version.arch"
            # Extract the package name (strip epoch, version, release, arch)
            match = re.match(r"^(?:\d+:)?([a-zA-Z0-9][a-zA-Z0-9._+-]*?)-\d+", line)
            if match:
                result.append(match.group(1))
            elif line and not line.startswith(" "):
                # Fallback: treat the whole line as the package name
                result.append(line)
        return result


class YumRepositories(FactBase):
    """
    Returns a list of installed yum repositories:

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
            "/etc/yum.conf",
            "/etc/yum.repos.d/*.repo",
        )

    @override
    def requires_command(self) -> str:
        return "yum"

    default = list

    @override
    def process(self, output):
        return parse_yum_repositories(output)
