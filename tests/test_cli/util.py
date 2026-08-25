import contextlib
from io import StringIO
from os import chdir, getcwd

import click

import pyinfra
from pyinfra_cli.cli import app


class CliResult:
    """Mimics the ``click.testing.Result`` interface used across the CLI tests."""

    def __init__(self, exit_code, stdout, stderr, exception):
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.output = stdout
        self.exception = exception


def run_cli(*arguments):
    cwd = getcwd()
    pyinfra.is_cli = True

    stdout_buffer = StringIO()
    stderr_buffer = StringIO()

    exit_code = 0
    exception = None

    try:
        with (
            contextlib.redirect_stdout(stdout_buffer),
            contextlib.redirect_stderr(stderr_buffer),
        ):
            try:
                app(list(arguments), exit_on_error=False)
            except click.ClickException as e:
                exception = e
                e.show()
                exit_code = e.exit_code
    except SystemExit as e:
        exit_code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    except BaseException as e:  # surface any error to the test as .exception
        exception = e
        exit_code = 1
    finally:
        pyinfra.is_cli = False
        chdir(cwd)

    return CliResult(
        exit_code=exit_code,
        stdout=stdout_buffer.getvalue(),
        stderr=stderr_buffer.getvalue(),
        exception=exception,
    )
