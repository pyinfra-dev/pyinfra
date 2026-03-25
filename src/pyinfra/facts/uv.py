"""
Present information provided by ``uv``:
    + available and installed versions of Python
    + installed Python packages and their versions
    + where the installed versions of Python are stored
    + where `tools are installed`
    + version of ``uv`` available


See https://docs.astral.sh/uv/ for details of ``uv``
"""

import json
from collections.abc import Iterable
from operator import itemgetter
from typing import cast

from typing_extensions import override

from pyinfra import logger
from pyinfra.api import StringCommand
from pyinfra.api.facts import FactBase
from pyinfra.facts.util.packaging import PackageVersionDict

UV_CMD = "uv"
MANAGED_PYTHON = "--managed-python"
ONLY_INSTALLED = "--only-installed"


def process_json(command: str, output: Iterable[str], key: str, value: str) -> PackageVersionDict:
    try:
        info = json.loads("\n".join(output))
    except json.decoder.JSONDecodeError:
        logger.warning(f"{command} json load failed, output was: '{output}")
        info = []
    if not isinstance(info, list):
        logger.warning(f"{command} produced unexpected output: '{output}")
        info = []

    return {v[key]: {v[value]} for v in sorted(info, key=itemgetter(key))}


class UvPipPackages(FactBase[PackageVersionDict]):
    """
    Provides the installed Python packages and their version.

    **Example:**

    .. code:: python

        {
            "requests": ["2.32.5"],
        }
    """

    @override
    @staticmethod
    def default() -> PackageVersionDict:
        return cast("PackageVersionDict", {})

    @override
    def requires_command(self, *args, **kwargs) -> str | None:
        return UV_CMD

    @override
    def command(self) -> StringCommand | str:
        return f"{UV_CMD} pip list --format json"

    @override
    def process(self, output: Iterable[str]) -> PackageVersionDict:
        return process_json(str(self.command()), output, "name", "version")


class UvAvailablePythonsByImplementation(FactBase[PackageVersionDict]):
    """
    Provides the implementation(s) of Python available for installation along with the versions(s)
    of the implementation(s).

        + is_managed: if set, only list Python implementations managed by `uv`. Default True

    **Example:**

    .. code:: python

        {
            "cpython-3.13.4-macos-aarch64-none": ["3.13.4"]
        }
    """

    are_installed = False

    @override
    @staticmethod
    def default() -> PackageVersionDict:
        return cast("PackageVersionDict", {})

    @override
    def requires_command(self, *args, **kwargs) -> str:
        return UV_CMD

    @override
    def command(self, is_managed: bool = True) -> StringCommand | str:
        managed = MANAGED_PYTHON if is_managed else ""
        installed = ONLY_INSTALLED if self.are_installed else ""
        self.cmd = f"{UV_CMD} python list {managed} {installed} --output-format=json"
        return self.cmd

    @override
    def process(self, output: Iterable[str]) -> PackageVersionDict:
        return process_json(str(self.cmd), output, "key", "version")


class UvAvailablePythonsByVersion(UvAvailablePythonsByImplementation):
    """
    Provides the version(s) of Python available for installation along with the implementation(s)
    of the version(s).

        + is_managed: if set, only list Python implementations managed by `uv`. Default True

    **Example:**

    .. code:: python

        {
            "3.13.4": ["cpython-3.13.4-macos-aarch64-none"]
        }
    """

    @override
    def process(self, output: Iterable[str]) -> PackageVersionDict:
        return process_json(str(self.cmd), output, "version", "key")


class UvInstalledPythonsByImplementation(UvAvailablePythonsByImplementation):
    """
    Provides the installed implementation(s) of Python along with the versions(s) of
    the implementation(s).

        + is_managed: if set, only list Python implementations managed by `uv`. Default True

    **Example:**

    .. code:: python

        {
            "cpython-3.13.4-macos-aarch64-none": ["3.13.4"]
        }
    """

    are_installed = True

    @override
    def process(self, output: Iterable[str]) -> PackageVersionDict:
        return process_json(str(self.cmd), output, "key", "version")


class UvInstalledPythonsByVersion(UvInstalledPythonsByImplementation):
    """
    Provides the installed versions of Python along with the implementation(s) of
    the version(s).

        + is_managed: if set, only list Python versions managed by `uv`. Default True

    **Example:**

    .. code:: python

        {
            "3.13.4": ["cpython-3.13.4-macos-aarch64-none"]
        }
    """

    @override
    def process(self, output: Iterable[str]) -> PackageVersionDict:
        return process_json(str(self.cmd), output, "version", "key")


class UvPythonDir(FactBase[str]):
    """
    Provides the directory in which uv installs Python implementations.

    **Example:**

    .. code:: python

        /home/someone/.local/share/uv/python
    """

    @override
    @staticmethod
    def default() -> str:
        return ""

    @override
    def requires_command(self, *args, **kwargs) -> str:
        return UV_CMD

    @override
    def command(self) -> StringCommand | str:
        return f"{UV_CMD} python dir 2>/dev/null"

    @override
    def process(self, output: Iterable[str]) -> str:
        output_iter = iter(output)
        if ((result := next(output_iter, None)) is not None) and (next(output_iter, None) is None):
            return result

        logger.warning(f"ignoring unexpected output from {self.command()}: '{output}'")
        return ""


class UvToolDir(UvPythonDir):
    """
    Provides the directory in which uv installs tools.

    **Example:**

    .. code:: python

        /home/someone/.local/share/uv/tools
    """

    @override
    def command(self) -> StringCommand | str:
        return f"{UV_CMD} tool dir 2>/dev/null"


class UvTools(FactBase[PackageVersionDict]):
    """
    Provides the tool(s) currently installed along with their version(s).

    **Example:**

    .. code:: python

        {
            "pyinfra": "3.4.1"
        }
    """

    # the output is in line pairs:
    #   pyinfra v3.4.1
    #   - pyinfra

    @override
    @staticmethod
    def default() -> PackageVersionDict:
        return cast("PackageVersionDict", {})

    @override
    def requires_command(self, *args, **kwargs) -> str:
        return UV_CMD

    @override
    def command(self) -> StringCommand | str:
        return f"{UV_CMD} tool list 2>/dev/null"

    # TODO - use JSON when available (https://github.com/astral-sh/uv/issues/10219)
    @override
    def process(self, output: Iterable[str]) -> PackageVersionDict:
        result = {}
        for line in output:
            if line.startswith("- "):
                continue  # skip the names of the commands that have been added
            if len(pieces := line.split(" ")) > 1:
                result[pieces[0]] = {pieces[1].removeprefix("v")}
            else:
                logger.warning(f"ignoring unexpected output from {self.command()}: {line}")
        return result


class UvVersion(FactBase[str]):
    """
    Provides the version of uv installed.

    **Example:**

    .. code:: python

        uv 0.8.5 (Homebrew 2025-08-05)
    """

    @override
    @staticmethod
    def default() -> str:
        return ""

    @override
    def requires_command(self, *args, **kwargs) -> str:
        return UV_CMD

    @override
    def command(self) -> str | StringCommand:
        return f"{UV_CMD} --version"

    @override
    def process(self, output: Iterable[str]) -> str:
        output_iter = iter(output)
        if ((result := next(output_iter, None)) is not None) and (next(output_iter, None) is None):
            return result
        logger.warning(f"ignoring unexpected output from '{self.command()}': '{output}'")
        return ""
