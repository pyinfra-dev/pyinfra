from pyinfra.api import FactBase

from .util.packaging import parse_packages

PACMAN_REGEX = r'^([a-zA-Z\-]+)\s([0-9\._+a-z\-]+)'


class PacmanUnpackGroups(FactBase):
    '''
    Gets a list of packages/groups and returns the
    packages and the groups unpacked into packages:

    .. code:: python

        [
            'package_name',
        [
    '''

    requires_command = 'pacman'

    default = list

    def command(self, pkg_list):
        pkg_str = ' '.join(pkg_list)
        return 'pacman -S --print-format "%n" {0}'.format(pkg_str)

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
