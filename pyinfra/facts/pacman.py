from pyinfra.api import FactBase

from .util.packaging import parse_packages

PACMAN_REGEX = r'^([0-9a-zA-Z\-]+)\s([0-9\._+a-z\-]+)'


class PacmanUnpackGroup(FactBase):
    '''
    Returns a list of actual packages belonging to the provided package name,
    expanding groups or virtual packages.

    .. code:: python

        [
            'package_name',
        ]
    '''

    requires_command = 'pacman'

    default = list

    def command(self, name):
        # Accept failure here (|| true) for invalid/unknown packages
        return 'pacman -S --print-format "%n" {0} || true'.format(name)

    def process(self, output):
        return output


class PacmanPackages(FactBase):
    '''
    Returns a dict of installed pacman packages:

    .. code:: python

        {
            'package_name': ['version'],
        }
    '''

    command = 'pacman -Q'
    requires_command = 'pacman'

    default = dict

    def process(self, output):
        return parse_packages(PACMAN_REGEX, output)
