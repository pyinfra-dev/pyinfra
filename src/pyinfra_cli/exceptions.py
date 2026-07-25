import sys
from inspect import getframeinfo
from traceback import walk_tb
from types import ModuleType, TracebackType

from rich.console import Console
from rich.traceback import Traceback
from typing_extensions import override

import pyinfra
from pyinfra import logger
from pyinfra.api.exceptions import (
    ArgumentTypeError,
    ConnectorDataTypeError,
    OperationError,
    PyinfraError,
)
from pyinfra.api.util import PYINFRA_INSTALL_DIR

from .console import console, format_text

# Modules whose frames are collapsed in rendered tracebacks so the user's deploy
# code stands out rather than pyinfra/gevent/cyclopts internals.
_TRACEBACK_SUPPRESS: list[str | ModuleType] = ["gevent", "cyclopts", pyinfra]


def _rich_traceback(exc: BaseException) -> Traceback:
    """Build a Rich ``Traceback`` for a wrapped exception.

    The wrapping ``CliException`` stashes the live traceback on the original
    exception as ``_traceback``; fall back to ``__traceback__`` just in case.
    """
    tb = getattr(exc, "_traceback", None) or exc.__traceback__
    return Traceback.from_exception(
        type(exc),
        exc,
        tb,
        suppress=_TRACEBACK_SUPPRESS,
        show_locals=False,
        word_wrap=True,
    )


def get_frame_line_from_tb(tb: TracebackType):
    frame_lines = list(walk_tb(tb))
    frame_lines.reverse()
    for frame, line in frame_lines:
        info = getframeinfo(frame)
        if info.filename.startswith(PYINFRA_INSTALL_DIR):
            continue
        return info


class CliException(Exception):
    """Base for pyinfra CLI errors, carrying a user-facing ``message``."""

    message: str

    def __init__(self, message: str = ""):
        self.message = message
        super().__init__(message)

    @override
    def __str__(self) -> str:
        return self.message

    def show(self) -> None:
        raise NotImplementedError


class WrappedError(CliException):
    def __init__(self, e: Exception):
        self.traceback = e.__traceback__
        self.exception = e

        # Pull message from the wrapped exception
        message = getattr(e, "message", e.args[0])
        if not isinstance(message, str):
            message = repr(message)
        super().__init__(message)

    @override
    def show(self) -> None:
        name = "unknown error"

        if isinstance(self.exception, ConnectorDataTypeError):
            name = "Connector data type error"
        elif isinstance(self.exception, ArgumentTypeError):
            name = "Argument type error"
        elif isinstance(self.exception, OperationError):
            name = "Operation error"
        elif isinstance(self.exception, PyinfraError):
            name = "pyinfra error"
        elif isinstance(self.exception, IOError):
            name = "Local IO error"

        if self.traceback:
            info = get_frame_line_from_tb(self.traceback)
            if info:
                name = f"{name} in {info.filename} line {info.lineno}"

        logger.warning(
            f"--> {format_text(name, 'red', bold=True)}: {self}",
        )


class CliError(CliException):
    @override
    def show(self) -> None:
        logger.warning(
            f"--> {format_text('pyinfra error', 'red', bold=True)}: {self}",
        )


class UnexpectedExternalError(CliException):
    def __init__(self, e, filename):
        _, _, traceback = sys.exc_info()
        e._traceback = traceback
        self.exception = e
        self.filename = filename
        super().__init__(str(e))

    @override
    def show(self) -> None:
        logger.warning(
            "--> {}:\n".format(
                format_text(
                    f"An exception occurred in: {self.filename}",
                    "red",
                    bold=True,
                ),
            ),
        )

        console.print(_rich_traceback(self.exception))


class UnexpectedInternalError(CliException):
    def __init__(self, e):
        _, _, traceback = sys.exc_info()
        e._traceback = traceback
        self.exception = e
        super().__init__(str(e))

    @override
    def show(self) -> None:
        console.print(
            "--> {}:\n".format(
                format_text(
                    "An internal exception occurred",
                    "red",
                    bold=True,
                ),
            ),
        )

        traceback = _rich_traceback(self.exception)
        console.print(traceback)

        # Persist an uncoloured copy of the same traceback for bug reports.
        with open("pyinfra-debug.log", "w", encoding="utf-8") as f:
            file_console = Console(file=f, width=100, force_terminal=False, no_color=True)
            file_console.print(traceback)

        logger.debug(str(self.exception))

        console.print(
            f"--> The full traceback has been written to {format_text('pyinfra-debug.log', bold=True)}",
        )
        console.print(
            "--> If this is unexpected please consider submitting a bug report "
            "on GitHub, for more information run `pyinfra --support`."
        )
