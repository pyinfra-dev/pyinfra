from pyinfra.api import FactBase

from .util.packaging import parse_yum_repositories


class DnfRepositories(FactBase):
    '''
    Returns a list of installed dnf repositories:

    .. code:: python

        {
            'baseurl': 'http://archive.ubuntu.org',
        },
        ...
    '''

    command = (
        'cat /etc/dnf.conf /etc/dnf.repos.d/*.repo '
        '/etc/yum.repos.d/*.repo 2> /dev/null || true'
    )

    default = list

    def process(self, output):
        return parse_yum_repositories(output)
