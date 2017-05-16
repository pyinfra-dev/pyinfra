# pyinfra
# File: pyinfra/cli/arguments.py
# Desc: argument parsing for the CLI

import shlex

from importlib import import_module

import click

from pyinfra import logger, pseudo_host
from pyinfra.local import exec_file

from . import CliError


def _parse_arg(arg):
    if arg.lower() == 'false':
        return False

    if arg.lower() == 'true':
        return True

    return arg


def parse_argstring(argstring):
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
        args = parse_argstring(args_string)

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


def load_deploy_file(state, filename):
    for host in state.inventory:
        pseudo_host.set(host)

        exec_file(filename)

        state.ready_host(host)

        logger.info('{0} {1} {2}'.format(
            '[{}]'.format(click.style(host.name, bold=True)),
            click.style('Ready:', 'green'),
            click.style(filename, bold=True),
        ))

    # Remove any pseudo host
    pseudo_host.reset()

    # Un-ready the hosts - this is so that any hooks or callbacks during the deploy
    # can still use facts as expected.
    state.ready_hosts = set()
