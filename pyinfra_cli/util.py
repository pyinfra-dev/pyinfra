# pyinfra
# File: pyinfra_cli/arguments.py
# Desc: general utilities for the pyinfra CLI

from __future__ import division, print_function

import json
import os
import sys

from collections import deque
from contextlib import contextmanager
from datetime import datetime
from importlib import import_module
from threading import Event, Thread
from time import sleep
from types import FunctionType

# py2/3 switcheroo
try:
    from StringIO import StringIO
    from cStringIO import OutputType, InputType
    from types import FileType
    io_bases = (FileType, OutputType, InputType, StringIO)

except ImportError:
    from io import IOBase
    io_bases = IOBase

import click

from pyinfra import logger, pseudo_host, pseudo_state
from pyinfra.api.attrs import FallbackAttrData
from pyinfra.hook import HOOKS

from .compile import compile_deploy_code
from .exceptions import CliError
from .legacy import parse_legacy_argstring

PYTHON_CODES = {}
WAIT_CHARS = deque(('-', '/', '|', '\\'))


def print_spinner(stop_event, progress_queue):
    if os.environ.get('PYINFRA_PROGRESS') == 'off':
        return

    progress = ''
    text = ''

    while True:
        # Stop when asked too
        if stop_event.is_set():
            break

        WAIT_CHARS.rotate(1)

        try:
            progress = progress_queue[-1]
        except IndexError:
            pass

        # Add 5 spaces on the end to overwrite any thing "pushed" right by the
        # user typing.
        text = '    {0}     \r'.format(
            ' '.join((WAIT_CHARS[0], progress)),
        )

        sys.stdout.write(text)
        sys.stdout.flush()

        sleep(1 / 20)

    # Write out spaces to clear/match the last printed text line
    sys.stdout.write('{0}\r'.format(''.join(' ' for _ in range(len(text)))))


@contextmanager
def progress_spinner(length):
    if not isinstance(length, int):
        length = len(length)

    stop_event = Event()
    progress_queue = deque(('0% (0/{0})'.format(length),))
    complete_items = []

    def progress():
        complete_items.append(True)
        complete = len(complete_items)

        percentage_complete = int(round(complete / length * 100))

        progress_queue.append('{0}% ({1}/{2})'.format(
            percentage_complete,
            complete,
            length,
        ))

    # Kick off the spinner thread
    spinner_thread = Thread(
        target=print_spinner,
        args=(stop_event, progress_queue),
    )
    spinner_thread.daemon = True
    spinner_thread.start()

    # Yield allowing the actual code the spinner waits for to run
    yield progress

    # Finally, stop the spinner
    stop_event.set()
    spinner_thread.join()


def exec_file(filename, return_locals=False, is_deploy_code=False):
    '''
    Execute a Python file and optionally return it's attributes as a dict.
    '''

    if filename not in PYTHON_CODES:
        with open(filename, 'r') as f:
            code = f.read()

        if is_deploy_code:
            code = compile_deploy_code(code)

        code = compile(code, filename, 'exec')
        PYTHON_CODES[filename] = code

    # Create some base attributes for our "module"
    data = {
        '__file__': filename,
        'state': pseudo_state,
    }

    # Execute the code with locals/globals going into the dict above
    exec(PYTHON_CODES[filename], data)

    return data


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

    elif isinstance(obj, FallbackAttrData):
        return obj.dict()

    elif isinstance(obj, io_bases):
        if hasattr(obj, 'name'):
            return 'File: {0}'.format(obj.name)

        elif hasattr(obj, 'template'):
            return 'Template: {0}'.format(obj.template)

        obj.seek(0)
        return 'In memory file: {0}'.format(obj.read())

    elif isinstance(obj, set):
        return list(obj)

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

    return arg


def get_operation_and_args(commands):
    operation_name = commands[0]

    # Get the module & operation name
    op_module, op_name = operation_name.split('.')

    try:
        op_module = import_module('pyinfra.modules.{0}'.format(op_module))
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
            # COMPAT w/ <0.7
            # TODO: remove this conditional
            if ',' in operation_args[0]:
                operation_args = parse_legacy_argstring(operation_args[0])

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


def load_deploy_file(state, filename, progress):
    for host in state.inventory:
        # Don't load for anything within our (top level, --limit) limit
        if (
            isinstance(state.limit_hosts, list)
            and host not in state.limit_hosts
        ):
            continue

        pseudo_host.set(host)

        exec_file(filename, is_deploy_code=True)
        progress()

        logger.info('{0} {1} {2}'.format(
            host.print_prefix,
            click.style('Ready:', 'green'),
            click.style(filename, bold=True),
        ))

    # Remove any pseudo host
    pseudo_host.reset()
