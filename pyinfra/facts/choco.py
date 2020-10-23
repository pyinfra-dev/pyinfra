from pyinfra.api import FactBase

from .util.packaging import parse_packages

CHOCO_REGEX = r'^([a-zA-Z0-9\.\-\+\_]+)\s([0-9\.]+)$'


class ChocoPackages(FactBase):
    '''
    Returns a dict of installed choco (Chocolatey) packages:

    .. code:: python

        {
            'package_name': ['version'],
        }
    '''

    command = 'choco list --local-only'
    shell_executable = 'ps'

    default = dict

    def process(self, output):
        return parse_packages(CHOCO_REGEX, output)


class ChocoVersion(FactBase):
    '''
    Returns the choco (Chocolatey) version.
    '''

    command = 'choco --version'

    @staticmethod
    def process(output):
        return ''.join(output).replace('\n', '')
