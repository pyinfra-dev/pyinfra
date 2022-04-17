from pyinfra.api import FactBase

from .util import make_cat_files_command
from .util.packaging import parse_yum_repositories


class DnfRepositories(FactBase):
    """
    Returns a list of installed dnf repositories:

    .. code:: python

        [
            {
                "name": "CentOS-$releasever - Apps",
                "baseurl": "http://mirror.centos.org/$contentdir/$releasever/Apps/$basearch/os/",
                "gpgcheck": "1",
                "enabled": "1",
                "gpgkey": "file:///etc/pki/rpm-gpg/RPM-GPG-KEY-centosofficial",
            },
        ]
    """

    command = make_cat_files_command(
        "/etc/dnf.conf",
        "/etc/dnf.repos.d/*.repo",
        "/etc/yum.repos.d/*.repo",
    )
    requires_command = "dnf"

    default = list

    def process(self, output):
        return parse_yum_repositories(output)
