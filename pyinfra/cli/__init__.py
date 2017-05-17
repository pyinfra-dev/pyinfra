# pyinfra
# File: pyinfra/cli.py
# Desc: pyinfra CLI helpers

from __future__ import print_function

import sys

from datetime import datetime

from types import FunctionType

# py2/3 switcheroo
try:
    from StringIO import StringIO
    from cStringIO import OutputType, InputType
    io_bases = (file, OutputType, InputType, StringIO)

except ImportError:
    from io import IOBase
    io_bases = IOBase

import click
import six

from pyinfra import logger, pseudo_host

from pyinfra.api.exceptions import PyinfraError
from pyinfra.hook import Error as HookError, HOOKS


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


def run_hook(state, hook_name, hook_data):
    hooks = HOOKS[hook_name]

    if hooks:
        for hook in hooks:
            print('--> Running hook: {0}/{1}'.format(
                hook_name,
                click.style(hook.__name__, bold=True),
            ))
            hook(hook_data, state)

        print()


def json_encode(obj):
    if isinstance(obj, FunctionType):
        return obj.__name__

    elif isinstance(obj, datetime):
        return obj.isoformat()

    elif isinstance(obj, io_bases):
        if hasattr(obj, 'name'):
            return 'File: {0}'.format(obj.name)

        elif hasattr(obj, 'template'):
            return 'Template: {0}'.format(obj.template)

        obj.seek(0)
        return 'In-memory file: {0}'.format(obj.read())

    elif isinstance(obj, set):
        return list(obj)

    else:
        raise TypeError('Cannot serialize: {0}'.format(obj))
