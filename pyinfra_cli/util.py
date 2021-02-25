from __future__ import division, print_function

import json

from datetime import datetime
from importlib import import_module
from types import FunctionType, ModuleType

# py2/3 switcheroo
try:  # pragma: no cover
    from StringIO import StringIO
    from cStringIO import OutputType, InputType
    from types import FileType
    io_bases = (FileType, OutputType, InputType, StringIO)

except ImportError:  # pragma: no cover
    from io import IOBase
    io_bases = IOBase

import click
import six

from pyinfra import logger, pseudo_host, pseudo_state
from pyinfra.api.command import PyinfraCommand
from pyinfra.api.util import FallbackDict

from .exceptions import CliError, UnexpectedExternalError

# Cache for compiled Python deploy code
PYTHON_CODES = {}


def exec_file(filename, return_locals=False, is_deploy_code=False):
    '''
    Execute a Python file and optionally return it's attributes as a dict.
    '''

    pseudo_state.current_exec_filename = filename

    if filename not in PYTHON_CODES:
        with open(filename, 'r') as f:
            code = f.read()

        code = compile(code, filename, 'exec')
        PYTHON_CODES[filename] = code

    # Create some base attributes for our "module"
    data = {
        '__file__': filename,
    }

    # Execute the code with locals/globals going into the dict above
    try:
        exec(PYTHON_CODES[filename], data)
    except Exception as e:
        raise UnexpectedExternalError(e, filename)

    return data


def json_encode(obj):
    # pyinfra types
    if isinstance(obj, FallbackDict):
        return obj.dict()

    elif isinstance(obj, PyinfraCommand):
        return repr(obj)

    # Python types
    elif isinstance(obj, ModuleType):
        return 'Module: {0}'.format(obj.__name__)

    elif isinstance(obj, FunctionType):
        return 'Function: {0}'.format(obj.__name__)

    elif isinstance(obj, datetime):
        return obj.isoformat()

    elif isinstance(obj, io_bases):
        if hasattr(obj, 'name'):
            return 'File: {0}'.format(obj.name)

        elif hasattr(obj, 'template'):
            return 'Template: {0}'.format(obj.template)

        obj.seek(0)
        return 'In memory file: {0}'.format(obj.read())

    elif isinstance(obj, set):
        return sorted(list(obj))

    elif isinstance(obj, six.binary_type):
        return obj.decode()

    else:
        raise TypeError('Cannot serialize: {0} ({1})'.format(type(obj), obj))


def _parse_arg(arg):
    if isinstance(arg, list):
        return [_parse_arg(a) for a in arg]

    if arg.lower() == 'false':
        return False

    if arg.lower() == 'true':
        return True

    try:
        return int(arg)
    except (TypeError, ValueError):
        pass

    try:
        return json.loads(arg)
    except ValueError:
        pass

    return arg


def get_operation_and_args(commands):
    operation_name = commands[0]

    # Get the module & operation name
    op_module, op_name = operation_name.split('.')

    # Try to load the requested operation from the main operations package.
    # If that fails, try to load from the user's operations package.
    try:
        op_module = import_module('pyinfra.operations.{0}'.format(op_module))
    except ImportError:
        try:
            op_module = import_module(str(op_module))
        except ImportError:
            raise CliError('No such module: {0}'.format(op_module))

    op = getattr(op_module, op_name, None)
    if not op:
        raise CliError('No such operation: {0}'.format(operation_name))

    # Parse the arguments
    operation_args = commands[1:]

    if len(operation_args) == 1:
        # Check if we're JSON (in which case we expect a list of two items:
        # a list of args and a dict of kwargs).
        try:
            args, kwargs = json.loads(operation_args[0])
            return op, (args, kwargs)
        except ValueError:
            pass

    args = [
        _parse_arg(arg)
        for arg in operation_args if '=' not in arg
    ]

    kwargs = {
        key: _parse_arg(value)
        for key, value in [
            arg.split('=', 1)
            for arg in operation_args if '=' in arg
        ]
    }

    return op, (args, kwargs)


def load_deploy_file(state, filename):
    state.current_deploy_filename = filename

    # Copy the inventory hosts (some might be removed during deploy)
    hosts = list(state.inventory.iter_active_hosts())

    for host in hosts:
        pseudo_host.set(host)

        exec_file(filename)

        logger.info('{0}{1} {2}'.format(
            host.print_prefix,
            click.style('Ready:', 'green'),
            click.style(filename, bold=True),
        ))

    # Remove any pseudo host
    pseudo_host.reset()
