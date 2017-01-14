# pyinfra
# File: pyinfra/cli.py
# Desc: pyinfra CLI helpers

from __future__ import print_function

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

from termcolor import colored

from pyinfra.hook import HOOKS
from pyinfra.api.exceptions import PyinfraError


class CliError(PyinfraError):
    pass


def run_hook(state, hook_name, hook_data):
    hooks = HOOKS[hook_name]

    if hooks:
        for hook in hooks:
            print('--> Running hook: {0}/{1}'.format(
                hook_name,
                colored(hook.__name__, attrs=['bold'])
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
