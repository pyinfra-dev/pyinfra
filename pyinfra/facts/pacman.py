from pyinfra.api import FactBase

from .util.packaging import parse_packages

PACMAN_REGEX = r'^([a-zA-Z\-]+)\s([0-9\._+a-z\-]+)'


class PacmanPackages(FactBase):
    '''
    Returns a dict of installed pacman packages:

    .. code:: python

        'package_name': ['version'],
        ...
    '''

    command = 'pacman -Q'
    default = dict

    def process(self, output):
        return parse_packages(PACMAN_REGEX, output)
