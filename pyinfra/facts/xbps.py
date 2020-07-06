from pyinfra.api import FactBase

from .util.packaging import parse_packages


class XbpsPackages(FactBase):
    '''
    Returns a dict of installed XBPS packages:

    .. code:: python

        'package_name': ['version'],
        ...
    '''

    command = 'xbps-query -l'
    regex = r'^.. ([a-zA-Z0-9_\-\+]+)\-([0-9a-z_\.]+)'
    default = dict
    use_default_on_error = True

    def process(self, output):
        return parse_packages(self.regex, output)
