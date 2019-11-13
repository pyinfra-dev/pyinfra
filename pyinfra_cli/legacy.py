import shlex
import sys

from os import path

import click
import six

from docopt import docopt

from .exceptions import CliError


DOCOPT_STRING = '''
pyinfra
Docs: pyinfra.readthedocs.io

Usage:
    pyinfra -i INVENTORY DEPLOY [-vv options]
    pyinfra -i INVENTORY --run OP ARGS [-vv options]
    pyinfra -i INVENTORY --run COMMAND [-vv options]
    pyinfra -i INVENTORY --fact FACT [-vv options]
    pyinfra -i INVENTORY [DEPLOY] --debug-data [options]
    pyinfra (--facts | --help | --version)

Deploy options:
    DEPLOY               Deploy script filename.
    -i INVENTORY         Inventory script filename or single hostname.
    --run OP ARGS        Run a single operation with args.
          COMMAND        Run a command using the server.shell operation.
    --fact FACT          Name of fact to run/test.
    --limit HOSTNAME     Limit the inventory, supports *wildcards and group names.
    --serial             Run commands on one host at a time.
    --no-wait             Don't wait for all hosts at each operation.
    -v -vv               Prints remote input/output in realtime. -vv prints facts output.
    --dry                Only print proposed changes.
    --debug              Print debug info.
    --debug-data         Print inventory hosts, data and exit (no connect/deploy).
    --debug-state        Print state information and exit (no deploy like --dry).

Config options:
    -p --port PORT       SSH port number.
    -u --user USER       SSH user.
    --key FILE           SSH private key.
    --key-password PASS  SSH key password.
    --sudo               Use sudo.
    --sudo-user USER     Which user to sudo to.
    --su-user USER
    --password PASS      SSH password auth (bad).
    --parallel NUM       Number of parallel processes.
    --fail-percent NUM   Percentage of hosts that can fail before exiting.

Experimental options:
    --enable-pipelining  Enable fact pipelining.
'''

ARGUMENT_KEY_CHANGES = {
    'verbose': 'verbosity',
}


def run_main_with_legacy_arguments(main):
    # Get arguments
    arguments = docopt(DOCOPT_STRING, version='pyinfra-0.3')

    # Prepare arguments
    arguments = setup_arguments(arguments)

    kwargs = {
        (
            ARGUMENT_KEY_CHANGES[key]
            if key in ARGUMENT_KEY_CHANGES
            else key
        ): value
        for key, value in six.iteritems(arguments)
    }

    commands = []

    # Deploy a file
    deploy = kwargs.pop('deploy')
    if deploy:
        commands.append(deploy)

    # Test a fact
    fact = kwargs.pop('fact')
    if fact:
        commands.extend(('fact', fact))

    # Single operations
    op = kwargs.pop('op')
    op_args = kwargs.pop('op_args')
    if op:
        commands.extend((op, op_args))

    kwargs['commands'] = commands

    print(click.style(
        'Falling back to old legacy v<0.4 CLI, in future please use:',
        'yellow',
    ))
    print()
    print(click.style('    pyinfra [OPTIONS] {0} {1}'.format(
        kwargs['inventory'],
        ' '.join(commands),
    ), bold=True))

    try:
        main(**kwargs)
    except CliError as e:
        click.echo('Error: {0}({1})'.format(
            e.__class__.__name__,
            click.style(e.message, 'red', bold=True),
        ))
        sys.exit(1)

    finally:
        print()
        print(click.style(
            'pyinfra was executed with the legacy v<0.4 CLI, in future please use:',
            'yellow',
        ))
        print()
        print(click.style('    pyinfra [OPTIONS] {0} {1}'.format(
            kwargs['inventory'],
            ' '.join(commands),
        ), bold=True))


def parse_legacy_argstring(argstring):
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

    return op_string, args_string


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
    }
