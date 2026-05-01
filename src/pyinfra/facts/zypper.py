from __future__ import annotations

from typing_extensions import override

from pyinfra.api import FactBase

from .util import make_cat_files_command_with_markers
from .util.packaging import REPO_FILENAME_MARKER, parse_zypper_repositories


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
                "baseurl": "http://download.opensuse.org/distribution/leap/$releasever/repo/oss/",
                "filename": "/etc/zypp/repos.d/oss.repo"
            },
        ]
    """

    @override
    def command(self) -> str:
        return make_cat_files_command_with_markers(
            REPO_FILENAME_MARKER,
            "/etc/zypp/repos.d/*.repo",
        )

    @override
    def requires_command(self) -> str:
        return "zypper"

    default = list

    @override
    def process(self, output):
        return parse_zypper_repositories(output)
