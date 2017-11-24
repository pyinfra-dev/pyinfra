# pyinfra
# File: pyinfra_cli/arguments.py
# Desc: general utilities for the pyinfra CLI

from __future__ import division, print_function

import json
import os
import shlex
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
    io_bases = (file, OutputType, InputType, StringIO)

except ImportError:
    from io import IOBase
    io_bases = IOBase

import click

from pyinfra import logger, pseudo_host
from pyinfra.api.util import exec_file
from pyinfra.hook import HOOKS

from .exceptions import CliError

WAIT_CHARS = deque(('-', '/', '|', '\\'))


def print_spinner(stop_event, progress_queue):
    if 'PYINFRA_NO_PROGRESS' in os.environ:
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
        return 'In memory file: {0}'.format(obj.read())

    elif isinstance(obj, set):
        return list(obj)

    else:
        raise TypeError('Cannot serialize: {0}'.format(obj))


def _parse_arg(arg):
    if isinstance(arg, list):
        return [_parse_arg(a) for a in arg]

    if arg.lower() == 'false':
        return False

    if arg.lower() == 'true':
        return True

    return arg


def _parse_argstring(argstring):
    '''
    Preparses CLI input:

    ``arg1,arg2`` => ``['arg1', 'arg2']``
    ``[item1, item2],arg2`` => ``[['item1', 'item2'], arg2]``
    '''

    argstring = argstring.replace(',', ' , ')
    argstring = argstring.replace('[', ' [ ')
    argstring = argstring.replace(']', ' ] ')

    argbits = shlex.split(argstring)
    args = []
    arg_buff = []
    list_buff = []
    in_list = False

    for bit in argbits:
        if bit == '[' and not in_list:
            in_list = True
            continue

        elif bit == ']' and in_list:
            in_list = False
            args.append(list_buff)
            list_buff = []
            continue

        elif bit == ',':
            if not in_list and arg_buff:
                args.append(''.join(arg_buff))
                arg_buff = []

            continue

        # Restore any broken up ,[]s
        bit = bit.replace(' , ', ',')
        bit = bit.replace(' [ ', '[')
        bit = bit.replace(' ] ', ']')

        if in_list:
            list_buff.append(bit)
        else:
            arg_buff.append(bit)

    if arg_buff:
        args.append(' '.join(arg_buff))

    return args


def get_operation_and_args(op_string, args_string):
    # Get the module & operation name
    op_module, op_name = op_string.split('.')

    try:
        op_module = import_module('pyinfra.modules.{0}'.format(op_module))
    except ImportError:
        raise CliError('No such module: {0}'.format(op_module))

    op = getattr(op_module, op_name, None)
    if not op:
        raise CliError('No such operation: {0}'.format(op_string))

    # Replace the args string with kwargs
    args = None

    if args_string:
        try:
            args, kwargs = json.loads(args_string)
            args = (args, kwargs)

        except ValueError:
            args = _parse_argstring(args_string)

            # Setup kwargs
            kwargs = [arg.split('=') for arg in args if '=' in arg]
            op_kwargs = {
                key: _parse_arg(value)
                for key, value in kwargs
            }

            # Get the remaining args
            args = [_parse_arg(arg) for arg in args if '=' not in arg]

            args = (args, op_kwargs)

    return op, args


def load_deploy_file(state, filename, progress):
    for host in state.inventory:
        pseudo_host.set(host)

        exec_file(filename)

        state.ready_host(host)
        progress()

        logger.info('{0} {1} {2}'.format(
            '[{}]'.format(click.style(host.name, bold=True)),
            click.style('Ready:', 'green'),
            click.style(filename, bold=True),
        ))

    # Remove any pseudo host
    pseudo_host.reset()

    # Un-ready the hosts - this is so that any hooks or callbacks during the
    # deploy can still use facts as expected.
    state.ready_host_names = set()
