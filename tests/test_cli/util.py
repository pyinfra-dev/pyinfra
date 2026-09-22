import contextlib
from io import StringIO
from os import chdir, getcwd

import pyinfra
import pyinfra_cli.console as cli_console
from pyinfra_cli.cli import app
from pyinfra_cli.exceptions import CliException


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

    # The whole CLI (cli/prints/log/virtualenv/exceptions/progress) shares the
    # single console instance from pyinfra_cli.console, so redirecting its file
    # captures all human output.  Machine-readable (--json) output goes to real
    # stdout via print(), captured with redirect_stdout below.
    console = cli_console.console
    stdout_console = cli_console.stdout_console
    original_console_file = console.file
    original_stdout_console_file = stdout_console.file
    console.file = stderr_buffer
    stdout_console.file = stdout_buffer

    exit_code = 0
    exception = None

    try:
        with contextlib.redirect_stdout(stdout_buffer):
            app(list(arguments), exit_on_error=False)
    except SystemExit as e:
        exit_code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    except CliException as e:
        exception = e
        exit_code = 1
    except BaseException as e:  # noqa: B036 - surface any error to the test as .exception
        exception = e
        exit_code = 1
    finally:
        console.file = original_console_file
        stdout_console.file = original_stdout_console_file
        pyinfra.is_cli = False
        chdir(cwd)

    return CliResult(
        exit_code=exit_code,
        stdout=stdout_buffer.getvalue(),
        stderr=stderr_buffer.getvalue(),
        exception=exception,
    )
