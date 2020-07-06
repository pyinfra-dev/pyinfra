from pyinfra.api import FactBase

from .util.packaging import parse_zypper_repositories


class ZypperRepositories(FactBase):
    '''
    Returns a list of installed zypper repositories:

    .. code:: python

        {
            'name': 'Main Repository',
            'enabled': '1',
            'autorefresh': '0',
            'baseurl': 'http://download.opensuse.org/distribution/leap/$releasever/repo/oss/',
            'type': 'rpm-md'
        },
        ...
    '''

    command = 'cat /etc/zypp/repos.d/*.repo 2> /dev/null || true'
    default = list
    use_default_on_error = True

    def process(self, output):
        return parse_zypper_repositories(output)
