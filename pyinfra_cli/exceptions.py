from __future__ import print_function

import sys

from traceback import format_exception, format_tb

import click

from pyinfra import logger, pseudo_host, pseudo_state
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
            # Get any operation meta + name
            op_name = None
            current_op_hash = pseudo_state.current_op_hash
            current_op_meta = pseudo_state.op_meta.get(current_op_hash)
            if current_op_meta:
                op_name = ', '.join(current_op_meta['names'])

            sys.stderr.write('--> {0}{1}{2}: '.format(
                pseudo_host.print_prefix,
                click.style(name, 'red', bold=True),
                ' (operation={0})'.format(op_name) if op_name else '',
            ))
        else:
            sys.stderr.write(
                '--> {0}: '.format(click.style(name, 'red', bold=True)),
            )

        logger.warning(self)


class UnexpectedError(click.ClickException):
    def __init__(self, e):
        self.e = e

    def show(self):
        sys.stderr.write('--> {0}:\n'.format(click.style(
            'An unexpected exception occurred',
            'red',
            bold=True,
        )))
        click.echo()

        traceback = getattr(self.e, '_traceback')
        traceback_lines = format_tb(traceback)
        traceback = ''.join(traceback_lines)

        # Syntax errors contain the filename/line/etc, but other exceptions
        # don't, so print the *last* call to stderr.
        if not isinstance(self.e, SyntaxError):
            sys.stderr.write(traceback_lines[-1])

        exception = ''.join(format_exception(self.e.__class__, self.e, None))
        sys.stderr.write(exception)

        with open('pyinfra-debug.log', 'w') as f:
            f.write(traceback)
            f.write(exception)

        logger.debug(traceback)
        logger.debug(exception)

        click.echo()
        click.echo('--> The full traceback has been written to {0}'.format(
            click.style('pyinfra-debug.log', bold=True),
        ))
