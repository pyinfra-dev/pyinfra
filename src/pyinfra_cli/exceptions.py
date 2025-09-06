import abc
import sys
from inspect import getframeinfo
from traceback import format_exception, format_tb, walk_tb
from types import TracebackType

import click
from typing_extensions import override

from pyinfra import logger
from pyinfra.api.exceptions import (
    ArgumentTypeError,
    ConnectorDataTypeError,
    OperationError,
    PyinfraError,
)
from pyinfra.api.util import PYINFRA_INSTALL_DIR


def get_frame_line_from_tb(tb: TracebackType):
    frame_lines = list(walk_tb(tb))
    frame_lines.reverse()
    for frame, line in frame_lines:
        info = getframeinfo(frame)
        if info.filename.startswith(PYINFRA_INSTALL_DIR):
            continue
        return info


class WrappedError(click.ClickException):
    def __init__(self, e: Exception):
        self.traceback = e.__traceback__
        self.exception = e

        # Pull message from the wrapped exception
        message = getattr(e, "message", e.args[0])
        if not isinstance(message, str):
            message = repr(message)
        self.message = message

    @override
    def show(self, file=None):
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
            "--> {0}: {1}".format(
                click.style(name, "red", bold=True),
                self,
            ),
        )


class CliError(click.ClickException):
    @override
    def show(self, file=None):
        logger.warning(
            "--> {0}: {1}".format(
                click.style("pyinfra error", "red", bold=True),
                self,
            ),
        )


class UnexpectedMixin(abc.ABC):
    exception: Exception
    traceback: TracebackType

    def get_traceback_lines(self):
        traceback = getattr(self.exception, "_traceback")
        return format_tb(traceback)

    def get_traceback(self):
        return "".join(self.get_traceback_lines())

    def get_exception(self):
        return "".join(format_exception(self.exception.__class__, self.exception, None))


class UnexpectedExternalError(click.ClickException, UnexpectedMixin):
    def __init__(self, e, filename):
        _, _, traceback = sys.exc_info()
        e._traceback = traceback
        self.exception = e
        self.filename = filename

    @override
    def show(self, file=None):
        logger.warning(
            "--> {0}:\n".format(
                click.style(
                    "An exception occurred in: {0}".format(self.filename),
                    "red",
                    bold=True,
                ),
            ),
        )

        click.echo("Traceback (most recent call last):", err=True)
        click.echo(self.get_traceback(), err=True, nl=False)
        click.echo(self.get_exception(), err=True)


class UnexpectedInternalError(click.ClickException, UnexpectedMixin):
    def __init__(self, e):
        _, _, traceback = sys.exc_info()
        e._traceback = traceback
        self.exception = e

    @override
    def show(self, file=None):
        click.echo(
            "--> {0}:\n".format(
                click.style(
                    "An internal exception occurred",
                    "red",
                    bold=True,
                ),
            ),
            err=True,
        )

        traceback_lines = self.get_traceback_lines()
        traceback = self.get_traceback()

        # Syntax errors contain the filename/line/etc, but other exceptions
        # don't, so print the *last* call to stderr.
        if not isinstance(self.exception, SyntaxError):
            sys.stderr.write(traceback_lines[-1])

        exception = self.get_exception()
        click.echo(exception, err=True)

        with open("pyinfra-debug.log", "w", encoding="utf-8") as f:
            f.write(traceback)
            f.write(exception)

        logger.debug(traceback)
        logger.debug(exception)

        click.echo(
            "--> The full traceback has been written to {0}".format(
                click.style("pyinfra-debug.log", bold=True),
            ),
            err=True,
        )
        click.echo(
            (
                "--> If this is unexpected please consider submitting a bug report "
                "on GitHub, for more information run `pyinfra --support`."
            ),
            err=True,
        )
