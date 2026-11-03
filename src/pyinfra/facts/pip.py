from __future__ import annotations

from typing_extensions import override

from pyinfra.api import FactBase, QuoteString, StringCommand

from .util.packaging import parse_packages
from .util.python import parse_python_version

PIP_REGEX = r"^([a-zA-Z0-9_\-\+\.]+)==([0-9\.]+[a-z0-9\-]*)$"


class PipPackages(FactBase):
    """
    Returns a dict of installed pip packages:

    .. code:: python

        {
            "package_name": ["version"],
        }
    """

    default = dict
    pip_command = "pip"

    @override
    def requires_command(self, pip=None):
        return pip or self.pip_command

    @override
    def command(self, pip=None):
        pip = pip or self.pip_command
        return f"{pip} freeze --all"

    @override
    def process(self, output):
        return parse_packages(PIP_REGEX, output)


class Pip3Packages(PipPackages):
    pip_command = "pip3"


class PythonVersion(FactBase[tuple[int, int, int] | None]):
    """
    Returns the version of a Python interpreter as a ``(major, minor, micro)`` tuple, or ``None``
    when it cannot be executed, eg a virtualenv whose base interpreter has been removed.

    + python: command name or path of the interpreter. Default ``python``

    .. code:: python

        (3, 14, 7)
    """

    @override
    def command(self, python: str = "python") -> StringCommand:
        return StringCommand(
            QuoteString(python),
            "-c",
            QuoteString("import sys; print(sys.version.split()[0])"),
            "|| true",
        )

    @override
    def process(self, output: list[str]) -> tuple[int, int, int] | None:
        return parse_python_version(output)
