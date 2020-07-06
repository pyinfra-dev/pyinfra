from pyinfra.api import FactBase

from .util.packaging import parse_packages


class PkgPackages(FactBase):
    '''
    Returns a dict of installed pkg packages:

    .. code:: python

        'package_name': ['version'],
        ...
    '''

    command = 'pkg info || pkg_info'
    regex = r'^([a-zA-Z0-9_\-\+]+)\-([0-9a-z\.]+)'
    default = dict
    use_default_on_error = True

    def process(self, output):
        return parse_packages(self.regex, output)
