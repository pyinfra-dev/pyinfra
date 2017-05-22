# pyinfra
# File: pyinfra_cli/exceptions.py
# Desc: the pyinfra CLI exception

from __future__ import print_function

import sys

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
