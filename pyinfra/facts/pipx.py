import re

from typing_extensions import override

from pyinfra.api import FactBase

from .util.packaging import parse_packages


# TODO: move to an utils file
def parse_environment(output):
    environment_REGEX = r"^(?P<key>[A-Z_]+)=(?P<value>.*)$"
    environment_variables = {}

    for line in output:
        matches = re.match(environment_REGEX, line)

        if matches:
            environment_variables[matches.group("key")] = matches.group("value")

    return environment_variables


PIPX_REGEX = r"^([a-zA-Z0-9_\-\+\.]+)\s+([0-9\.]+[a-z0-9\-]*)$"


class PipxPackages(FactBase):
    """
    Returns a dict of installed pipx packages:

    .. code:: python

        {
            "package_name": ["version"],
        }
    """

    default = dict

    @override
    def requires_command(self) -> str:
        return "pipx"

    @override
    def command(self) -> str:
        return "pipx list --short"

    @override
    def process(self, output):
        return parse_packages(PIPX_REGEX, output)


class PipxEnvironment(FactBase):
    """
    Returns a dict of pipx environment variables:

    .. code:: python

        {
            "PIPX_HOME": "/home/doodba/.local/pipx",
            "PIPX_BIN_DIR": "/home/doodba/.local/bin",
            "PIPX_SHARED_LIBS": "/home/doodba/.local/pipx/shared",
            "PIPX_LOCAL_VENVS": "/home/doodba/.local/pipx/venvs",
            "PIPX_LOG_DIR": "/home/doodba/.local/pipx/logs",
            "PIPX_TRASH_DIR": "/home/doodba/.local/pipx/.trash",
            "PIPX_VENV_CACHEDIR": "/home/doodba/.local/pipx/.cache",
        }
    """

    default = dict

    @override
    def requires_command(self) -> str:
        return "pipx"

    @override
    def command(self) -> str:
        return "pipx environment"

    @override
    def process(self, output):
        return parse_environment(output)
