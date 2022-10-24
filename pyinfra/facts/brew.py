import re

from pyinfra import logger
from pyinfra.api import FactBase

from .util.packaging import parse_packages

BREW_REGEX = r"^([^\s]+)\s([0-9\._+a-z\-]+)"


def new_cask_cli(version):
    """
    Returns true if brew is version 2.6.0 or later and thus has the new CLI for casks.
    i.e. we need to use brew list --cask instead of brew cask list
    See https://brew.sh/2020/12/01/homebrew-2.6.0/
    The version string returned by BrewVersion is a list of major, minor, patch version numbers
    """
    return (version[0] >= 3) or ((version[0] >= 2) and version[1] >= 6)


VERSION_MATCHER = re.compile(r"^Homebrew\s+(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+).*$")


def unknown_version():
    return [0, 0, 0]


class BrewVersion(FactBase):
    """
    Returns the version of brew installed as a semantic versioning tuple:

    .. code:: python

        [major, minor, patch]

    """

    command = "brew --version"
    requires_command = "brew"

    @staticmethod
    def default():
        return [0, 0, 0]

    def process(self, output):
        m = VERSION_MATCHER.match(output[0])
        if m is not None:
            return [int(m.group(key)) for key in ["major", "minor", "patch"]]
        logger.warning("could not parse version string from brew: %s", output[0])
        return self.default()


class BrewPackages(FactBase):
    """
    Returns a dict of installed brew packages:

    .. code:: python

        {
            "package_name": ["version"],
        }
    """

    command = "brew list --versions"
    requires_command = "brew"

    default = dict

    def process(self, output):
        return parse_packages(BREW_REGEX, output)


class BrewCasks(BrewPackages):
    """
    Returns a dict of installed brew casks:

    .. code:: python

        {
            "package_name": ["version"],
        }
    """

    command = (
        r'if brew --version | grep -q -e "Homebrew\ +(1\.|2\.[0-5]).*" 1>/dev/null;'
        r"then brew cask list --versions; else brew list --cask --versions; fi"
    )
    requires_command = "brew"


class BrewTaps(FactBase):
    """
    Returns a list of brew taps.
    """

    command = "brew tap"
    requires_command = "brew"

    default = list

    def process(self, output):
        return output
