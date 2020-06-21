from pyinfra.api import FactBase

from .util.packaging import parse_yum_repositories


class YumRepositories(FactBase):
    '''
    Returns a list of installed yum repositories:

    .. code:: python

        {
            'name': 'CentOS-$releasever - AppStream',
            'mirrorlist': 'http://mirrorlist.centos.org/?release=$releasever&arch=$basearch&repo=AppStream&infra=$infra',
            'gpgcheck': '1',
            'enabled': '1',
            'gpgkey': 'file:///etc/pki/rpm-gpg/RPM-GPG-KEY-centosofficial',
        },
        ...
    '''

    command = 'cat /etc/yum.conf /etc/yum.repos.d/*.repo 2> /dev/null || true'
    default = list

    def process(self, output):
        return parse_yum_repositories(output)
