from pyinfra.api import FactBase

from .util.packaging import parse_packages


class PkgPackages(FactBase):
    '''
    Returns a dict of installed pkg packages:

    .. code:: python

        'package_name': ['version'],
        ...
    '''

    command = (
        'which pkg > /dev/null && pkg info || '
        'which pkg_info > /dev/null && pkg_info || '
        'true'
    )
    regex = r'^([a-zA-Z0-9_\-\+]+)\-([0-9a-z\.]+)'
    default = dict

    def process(self, output):
        return parse_packages(self.regex, output)
