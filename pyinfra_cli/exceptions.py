# pyinfra
# File: pyinfra_cli/exceptions.py
# Desc: the pyinfra CLI exception

from __future__ import print_function

import sys

from traceback import format_exception, format_tb

import click
import six

from pyinfra import logger, pseudo_host
from pyinfra.api.exceptions import PyinfraError
from pyinfra.hook import Error as HookError


class CliError(PyinfraError, click.ClickException):
    def show(self):
        name = 'unknown error'

        if isinstance(self, HookError):
            name = 'hook error'

        elif isinstance(self, PyinfraError):
            name = 'pyinfra error'

        elif isinstance(self, IOError):
            name = 'local IO error'

        if pseudo_host.isset():
            sys.stderr.write('--> [{0}]: {1}: '.format(
                click.style(six.text_type(pseudo_host.name), bold=True),
                click.style(name, 'red', bold=True),
            ))
        else:
            sys.stderr.write(
                '--> {0}: '.format(click.style(name, 'red', bold=True)),
            )

        logger.warning(self)
        print()


class UnexpectedError(click.ClickException):
    def __init__(self, e):
        self.e = e

    def show(self):
        sys.stderr.write('--> {0}:\n'.format(click.style(
            'An unexpected exception occurred',
            'red',
            bold=True,
        )))
        print()

        traceback = getattr(self.e, '_traceback')
        traceback_lines = format_tb(traceback)
        traceback = ''.join(traceback_lines)

        # Syntax errors contain the filename/line/etc, but other exceptions
        # don't, so print the *last* call to stderr.
        if not isinstance(self.e, SyntaxError):
            sys.stderr.write(traceback_lines[-1])

        exception = ''.join(format_exception(self.e.__class__, self.e, None))
        sys.stderr.write(exception)

        # Write the full trace + exception to pyinfra-debug.log
        with open('pyinfra-debug.log', 'w') as f:
            f.write(traceback)
            f.write(exception)

        print()
        print('--> The full traceback has been written to {0}'.format(
            click.style('pyinfra-debug.log', bold=True),
        ))
