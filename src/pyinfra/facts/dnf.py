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
