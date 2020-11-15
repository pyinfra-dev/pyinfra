from __future__ import print_function

import sys

from traceback import format_exception, format_tb

import click

from pyinfra import logger, pseudo_host, pseudo_state
from pyinfra.api.exceptions import PyinfraError


class CliError(PyinfraError, click.ClickException):
    def show(self):
        name = 'unknown error'

        if isinstance(self, PyinfraError):
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


class UnexpectedMixin(object):
    def get_traceback_lines(self):
        traceback = getattr(self.e, '_traceback')
        return format_tb(traceback)

    def get_traceback(self):
        return ''.join(self.get_traceback_lines())

    def get_exception(self):
        return ''.join(format_exception(self.e.__class__, self.e, None))


class UnexpectedExternalError(click.ClickException, UnexpectedMixin):
    def __init__(self, e, filename):
        _, _, traceback = sys.exc_info()
        e._traceback = traceback
        self.e = e
        self.filename = filename

    def show(self):
        sys.stderr.write('--> {0}:\n'.format(click.style(
            'An unexpected exception occurred in: {0}'.format(self.filename),
            'red',
            bold=True,
        )))
        click.echo(err=True)

        sys.stderr.write(self.get_traceback())
        sys.stderr.write(self.get_exception())


class UnexpectedInternalError(click.ClickException, UnexpectedMixin):
    def __init__(self, e):
        _, _, traceback = sys.exc_info()
        e._traceback = traceback
        self.e = e

    def show(self):
        sys.stderr.write('--> {0}:\n'.format(click.style(
            'An unexpected internal exception occurred',
            'red',
            bold=True,
        )))
        click.echo(err=True)

        traceback_lines = self.get_traceback_lines()
        traceback = self.get_traceback()

        # Syntax errors contain the filename/line/etc, but other exceptions
        # don't, so print the *last* call to stderr.
        if not isinstance(self.e, SyntaxError):
            sys.stderr.write(traceback_lines[-1])

        exception = self.get_exception()
        sys.stderr.write(exception)

        with open('pyinfra-debug.log', 'w') as f:
            f.write(traceback)
            f.write(exception)

        logger.debug(traceback)
        logger.debug(exception)

        click.echo(err=True)
        click.echo('--> The full traceback has been written to {0}'.format(
            click.style('pyinfra-debug.log', bold=True),
        ), err=True)
        click.echo((
            '--> If this is unexpected please consider submitting a bug report '
            'on GitHub, for more information run `pyinfra --support`.'
        ), err=True)
