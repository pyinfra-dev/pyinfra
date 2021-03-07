from pyinfra.api import FactBase

from .util.packaging import parse_packages

BREW_REGEX = r'^([^\s]+)\s([0-9\._+a-z\-]+)'


class BrewPackages(FactBase):
    '''
    Returns a dict of installed brew packages:

    .. code:: python

        {
            'package_name': ['version'],
        }
    '''

    command = 'brew list --versions'
    requires_command = 'brew'

    default = dict

    def process(self, output):
        return parse_packages(BREW_REGEX, output)


class BrewCasks(BrewPackages):
    '''
    Returns a dict of installed brew casks:

    .. code:: python

        {
            'package_name': ['version'],
        }
    '''

    command = 'brew cask list --versions'
    requires_command = 'brew'


class BrewTaps(FactBase):
    '''
    Returns a list of brew taps.
    '''

    command = 'brew tap'
    requires_command = 'brew'

    default = list

    def process(self, output):
        return output
