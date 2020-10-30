from pyinfra.api import FactBase

from .util import make_cat_files_command
from .util.packaging import parse_zypper_repositories


class ZypperRepositories(FactBase):
    '''
    Returns a list of installed zypper repositories:

    .. code:: python

        [
            {
                'name': 'Main Repository',
                'enabled': '1',
                'autorefresh': '0',
                'baseurl': 'http://download.opensuse.org/distribution/leap/$releasever/repo/oss/',
                'type': 'rpm-md',
            },
        ]
    '''

    command = make_cat_files_command(
        '/etc/zypp/repos.d/*.repo',
    )
    requires_command = 'zypper'

    default = list

    def process(self, output):
        return parse_zypper_repositories(output)
