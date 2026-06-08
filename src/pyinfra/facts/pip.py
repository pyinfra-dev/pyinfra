from __future__ import annotations

import re

from typing_extensions import override

from pyinfra.api import FactBase, QuoteString, StringCommand
from pyinfra.api.command import make_formatted_string_command

from .util.packaging import parse_packages, pip_report_is_satisfied

PIP_REGEX = r"^([a-zA-Z0-9_\-\+\.]+)==([0-9\.]+[a-z0-9\-]*)$"
PIP_VERSION_REGEX = r"^pip\s+(\S+)"


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


class PipVersion(FactBase[str | None]):
    """
    Returns the version of ``pip`` (e.g. ``"24.0"``), or ``None`` if it cannot be determined.
    """

    @override
    def requires_command(self, pip=None) -> str:
        return pip or "pip"

    @override
    def command(self, pip=None) -> StringCommand:
        pip = pip or "pip"
        return make_formatted_string_command("{0} --version", QuoteString(pip))

    @override
    def process(self, output: list[str]) -> str | None:
        for line in output:
            matches = re.match(PIP_VERSION_REGEX, line)
            if matches:
                return matches.group(1)
        return None


class PipInstallDryRun(FactBase[bool]):
    """
    Whether ``pip install <spec>`` would change nothing in the current environment, using
    ``pip``'s own resolver via ``--dry-run``. Used to decide whether a spec carrying extras
    (e.g. ``foo[bar]``) is already satisfied when the bare package is installed.

    Requires pip >= 22.2 (for ``--dry-run``/``--report``).
    """

    default = bool  # False == not satisfied == install

    @override
    def requires_command(self, spec, pip=None) -> str:
        return pip or "pip"

    @override
    def command(self, spec, pip=None) -> StringCommand:
        pip = pip or "pip"
        # --report - writes the JSON resolution report to stdout; stderr noise is discarded.
        return make_formatted_string_command(
            "{0} install --dry-run --quiet --report - {1} 2> /dev/null",
            QuoteString(pip),
            QuoteString(spec),
        )

    @override
    def process(self, output: list[str]) -> bool:
        return pip_report_is_satisfied(output)
