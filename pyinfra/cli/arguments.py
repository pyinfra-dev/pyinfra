# pyinfra
# File: pyinfra/cli/arguments.py
# Desc: argument parsing for the CLI

import shlex

from importlib import import_module
from os import path

from pyinfra.api.facts import is_fact

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


def setup_op_and_args(op_string, args_string):
    op_bits = op_string.split('.')

    # If the op isn't <module>.<operation>
    if (
        len(op_bits) != 2
        # Modules/operations can only be lowercase alphabet
        or any(
            not bit.isalpha() or not bit.islower()
            for bit in op_bits
        )
    ):
        # Either default to server.shell w/op as command if no args are passed
        if not args_string:
            args_string = op_string
            op_bits = ['server', 'shell']

        # Or fail as it's an invalid op
        else:
            raise CliError('Invalid operation: {0}'.format(op_string))

    # Get the module & operation name
    op_module, op_name = op_bits

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


def setup_arguments(arguments):
    '''
    Prepares argumnents output by docopt.
    '''

    # Ensure parallel/port are numbers
    for key in ('--parallel', '--port', '--fail-percent'):
        if arguments[key]:
            try:
                arguments[key] = int(arguments[key])
            except ValueError:
                raise CliError('{0} is not a valid integer for {1}'.format(
                    arguments[key], key,
                ))

    # Prep --run OP ARGS
    if arguments['--run']:
        op, args = setup_op_and_args(arguments['--run'], arguments['ARGS'])
    else:
        op = args = None

    # Always assign empty args
    fact_args = []
    if arguments['--fact']:
        if ':' in arguments['--fact']:
            fact, fact_args = arguments['--fact'].split(':')
            fact_args = fact_args.split(',')
            arguments['--fact'] = fact

        # Ensure the fact exists
        if not is_fact(arguments['--fact']):
            raise CliError('Invalid fact: {0}'.format(arguments['--fact']))

    # Check deploy file exists
    if arguments['DEPLOY']:
        if not path.exists(arguments['DEPLOY']):
            raise CliError('Deploy file not found: {0}'.format(arguments['DEPLOY']))

    # Check our key file exists
    if arguments['--key']:
        if not path.exists(arguments['--key']):
            raise CliError('Private key file not found: {0}'.format(arguments['--key']))

    # Setup the rest
    return {
        # Deploy options
        'inventory': arguments['-i'],
        'deploy': arguments['DEPLOY'],
        'verbose': arguments['-v'],
        'dry': arguments['--dry'],
        'serial': arguments['--serial'],
        'no_wait': arguments['--no-wait'],
        'debug': arguments['--debug'],

        'debug_data': arguments['--debug-data'],
        'debug_state': arguments['--debug-state'],

        'fact': arguments['--fact'],
        'fact_args': fact_args,

        'limit': arguments['--limit'],
        'op': op,
        'op_args': args,

        # Config options
        'user': arguments['--user'],
        'key': arguments['--key'],
        'key_password': arguments['--key-password'],
        'password': arguments['--password'],
        'port': arguments['--port'],
        'sudo': arguments['--sudo'],
        'sudo_user': arguments['--sudo-user'],
        'su_user': arguments['--su-user'],
        'parallel': arguments['--parallel'],
        'fail_percent': arguments['--fail-percent'],

        # Misc
        'list_facts': arguments['--facts'],

        # Experimental
        'pipelining': arguments['--enable-pipelining'],
    }
