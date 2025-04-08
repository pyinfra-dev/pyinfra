from __future__ import annotations

from typing_extensions import override

from pyinfra.api import FactBase

from .util import make_cat_files_command
from .util.packaging import parse_zypper_repositories


class ZypperRepositories(FactBase):
    """
    Returns a list of installed zypper repositories:

    .. code:: python

        [
            {
                "name": "Main Repository",
                "enabled": "1",
                "autorefresh": "0",
                "baseurl": "http://download.opensuse.org/distribution/leap/$releasever/repo/oss/",
                "type": "rpm-md",
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
