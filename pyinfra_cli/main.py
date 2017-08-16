# pyinfra
# File: pyinfra_cli/main.py
# Desc: the actual CLI implementation

from __future__ import division, print_function

import logging
import sys

from os import getcwd, path

import click

from pyinfra import (
    __version__,
    logger,
    pseudo_inventory,
    pseudo_state,
)

from pyinfra.api import State
from pyinfra.api.attrs import FallbackAttrData
from pyinfra.api.connect import connect_all
from pyinfra.api.exceptions import PyinfraError
from pyinfra.api.facts import get_facts, is_fact
from pyinfra.api.operation import add_op
from pyinfra.api.operations import run_ops

from pyinfra.modules import server

from .config import load_config, load_deploy_config
from .exceptions import CliError
from .inventory import make_inventory
from .log import setup_logging
from .prints import (
    dump_state,
    print_facts,
    print_facts_list,
    print_inventory,
    print_meta,
    print_operations_list,
    print_results,
)
from .util import (
    get_operation_and_args,
    load_deploy_file,
    progress_spinner,
    run_hook,
)


# Exit handler
def _exit():
    print()
    print('<-- Thank you, goodbye')
    print()

    sys.exit(0)


def _print_facts(ctx, param, value):
    if not value:
        return

    print('--> Available facts:')
    print_facts_list()
    ctx.exit()


def _print_operations(ctx, param, value):
    if not value:
        return

    print('--> Available operations:')
    print_operations_list()
    ctx.exit()


@click.command()
@click.argument('inventory', nargs=1)
@click.argument('commands', nargs=-1, required=True)
@click.option(
    'verbosity', '-v',
    count=True,
    help='Print std[out|err] from operations/facts.',
)
@click.option('--user', help='SSH user to connect as.')
@click.option('--port', type=int, help='SSH port to connect to.')
@click.option('--key', type=click.Path(), help='Private key filename.')
@click.option('--key-password', help='Privte key password.')
@click.option('--password', help='SSH password.')
@click.option(
    '--sudo', is_flag=True, default=False,
    help='Whether to execute operations with sudo.',
)
@click.option('--sudo-user', help='Which user to sudo when sudoing.')
@click.option('--su-user', help='Which user to su to.')
@click.option('--parallel', type=int, help='Number of operations to run in parallel.')
@click.option('--fail-percent', type=int, help='% of hosts allowed to fail.')
@click.option(
    '--dry', is_flag=True, default=False,
    help='Don\'t execute operations on the remote host.',
)
@click.option(
    '--limit',
    help='Limit the inventory, supports *wildcards and group names.',
)
@click.option(
    '--no-wait', is_flag=True, default=False,
    help='Don\'t wait between operations for hosts to complete.',
)
@click.option(
    '--serial', is_flag=True, default=False,
    help='Run operations in serial, host by host.',
)
@click.option(
    '--debug', is_flag=True, default=False,
    help='Print debug info.',
)
@click.option(
    '--debug-data', is_flag=True, default=False,
    help='Print host/group data before operations and exit.',
)
@click.option(
    '--debug-state', is_flag=True, default=False,
    help='Print state data before operations and exit.',
)
@click.option(
    '--facts', is_flag=True, is_eager=True, callback=_print_facts,
    help='Print available facts list and exit.',
)
@click.option(
    '--operations', is_flag=True, is_eager=True, callback=_print_operations,
    help='Print available operations list and exit.',
)
@click.version_option(
    version=__version__,
    prog_name='pyinfra',
    message='%(prog)s: v%(version)s',
)
def cli(*args, **kwargs):
    '''
    pyinfra manages the state of one or more servers. It can be used for
    app/service deployment, config management and ad-hoc command execution.

    Documentation: pyinfra.readthedocs.io

    # INVENTORY

    \b
    + a file (inventory.py)
    + hostname (host.net)
    + Comma separated hostnames:
      host-1.net,host-2.net,@local

    # COMMANDS

    \b
    # Run one or more deploys against the inventory
    pyinfra INVENTORY deploy_web.py [deploy_db.py]...

    \b
    # Run a single operation against the inventory
    pyinfra INVENTORY server.user pyinfra,home=/home/pyinfra

    \b
    # Execute an arbitrary command on the inventory
    pyinfra INVENTORY exec -- echo "hello world"

    \b
    # Run one or more facts on the inventory
    pyinfra INVENTORY fact linux_distribution [users]...
    '''

    main(*args, **kwargs)


def main(*args, **kwargs):
    try:
        _main(*args, **kwargs)

    except PyinfraError as e:
        # Re-raise any internal exceptions that aren't handled by click as
        # CliErrors which are.
        if not isinstance(e, click.ClickException):
            message = getattr(e, 'message', e.args[0])
            raise CliError(message)

        raise


def _main(
    inventory, commands, verbosity,
    user, port, key, key_password, password,
    sudo, sudo_user, su_user,
    parallel, fail_percent,
    dry, limit, no_wait, serial,
    debug, debug_data, debug_state,
    facts=None, operations=None,
):
    print()
    print('### {0}'.format(click.style('Welcome to pyinfra', bold=True)))
    print()

    # Setup logging
    log_level = logging.DEBUG if debug else logging.INFO
    setup_logging(log_level)

    deploy_dir = getcwd()
    potential_deploy_dirs = []

    # This is the most common case: we have a deploy file so use it's
    # pathname - we only look at the first file as we can't have multiple
    # deploy directories.
    if commands[0].endswith('.py'):
        deploy_file_dir, _ = path.split(commands[0])
        above_deploy_file_dir, _ = path.split(deploy_file_dir)

        deploy_dir = deploy_file_dir

        potential_deploy_dirs.extend((
            deploy_file_dir, above_deploy_file_dir,
        ))

    # If we have a valid inventory, look in it's path and it's parent for
    # group_data or config.py to indicate deploy_dir (--fact, --run).
    if inventory.endswith('.py') and path.isfile(inventory):
        inventory_dir, _ = path.split(inventory)
        above_inventory_dir, _ = path.split(inventory_dir)

        potential_deploy_dirs.extend((
            inventory_dir, above_inventory_dir,
        ))

    for potential_deploy_dir in potential_deploy_dirs:
        logger.debug('Checking potential directory: {0}'.format(
            potential_deploy_dir,
        ))

        if any((
            path.isdir(path.join(potential_deploy_dir, 'group_data')),
            path.isfile(path.join(potential_deploy_dir, 'config.py')),
        )):
            logger.debug('Setting directory to: {0}'.format(potential_deploy_dir))
            deploy_dir = potential_deploy_dir
            break

    # List facts
    if commands[0] == 'fact':
        command = 'fact'

        fact_names = commands[1:]
        facts = []

        for name in fact_names:
            args = None

            if ':' in name:
                name, args = name.split(':', 1)
                args = args.split(',')

            if not is_fact(name):
                raise CliError('No fact: {0}'.format(name))

            facts.append((name, args))

        commands = facts

    # Execute a raw command with server.shell
    elif commands[0] == 'exec':
        command = 'exec'
        commands = commands[1:]

    # Deploy files(s)
    elif all(cmd.endswith('.py') for cmd in commands):
        command = 'deploy'
        commands = commands[0:]

        # Check each file exists
        for file in commands:
            if not path.exists(file):
                raise CliError('No deploy file: {0}'.format(file))

    # Operation w/optional args
    elif len(commands) == 2:
        command = 'op'
        commands = get_operation_and_args(
            commands[0], commands[1],
        )

    else:
        raise CliError('''Invalid commands: {0}

    Command usage:
    pyinfra INVENTORY deploy_web.py [deploy_db.py]...
    pyinfra INVENTORY server.user pyinfra,home=/home/pyinfra
    pyinfra INVENTORY exec -- echo "hello world"
    pyinfra INVENTORY fact os [users]...'''.format(commands))

    print('--> Loading config...')

    # Load up any config.py from the filesystem
    config = load_config(deploy_dir)

    # Load any hooks/config from the deploy file
    if command == 'deploy':
        load_deploy_config(commands[0], config)

    # Arg based config overrides
    if sudo:
        config.SUDO = True
        if sudo_user:
            config.SUDO_USER = sudo_user

    if su_user:
        config.SU_USER = su_user

    if parallel:
        config.PARALLEL = parallel

    if fail_percent is not None:
        config.FAIL_PERCENT = fail_percent

    print('--> Loading inventory...')

    # Load up the inventory from the filesystem
    inventory, inventory_group = make_inventory(
        inventory,
        deploy_dir=deploy_dir,
        limit=limit,
        ssh_user=user,
        ssh_key=key,
        ssh_key_password=key_password,
        ssh_password=password,
        ssh_port=port,
    )

    # If --debug-data dump & exit
    if debug_data:
        print_inventory(inventory)
        _exit()

    # Attach to pseudo inventory
    pseudo_inventory.set(inventory)

    # Create/set the state
    state = State(inventory, config)
    state.is_cli = True
    state.print_lines = True
    state.deploy_dir = deploy_dir

    # Setup printing on the new state
    print_output = verbosity > 0
    print_fact_output = verbosity > 1

    state.print_output = print_output  # -v
    state.print_fact_info = print_output  # -v
    state.print_fact_output = print_fact_output  # -vv

    # Attach to pseudo state
    pseudo_state.set(state)

    # Setup the data to be passed to config hooks
    hook_data = FallbackAttrData(
        state.inventory.get_override_data(),
        state.inventory.get_group_data(inventory_group),
        state.inventory.get_data(),
    )

    # Run the before_connect hook if provided
    run_hook(state, 'before_connect', hook_data)

    # Connect to all the servers
    print('--> Connecting to hosts...')
    with progress_spinner(state.inventory) as progress:
        connect_all(state, progress=progress)

    # Run the before_connect hook if provided
    run_hook(state, 'before_facts', hook_data)

    # Just getting a fact?
    #

    if command == 'fact':
        print()
        print('--> Gathering facts...')

        # Print facts as we get them
        state.print_fact_info = True

        # Print fact output with -v
        state.print_fact_output = print_output

        fact_data = {}

        with progress_spinner(commands) as progress:
            for i, (name, args) in enumerate(commands):
                fact_data[name] = get_facts(
                    state, name,
                    args=args,
                )
                progress()

        print_facts(fact_data)
        _exit()

    # Prepare the deploy!
    #

    # Execute a raw command with server.shell
    if command == 'exec':
        # Print the output of the command
        state.print_output = True

        add_op(
            state, server.shell,
            ' '.join(commands),
        )

    # Deploy files(s)
    elif command == 'deploy':
        print()
        print('--> Preparing operations...')

        # Number of "steps" to make = number of files * number of hosts
        prepare_steps = len(commands) * len(state.inventory)
        with progress_spinner(prepare_steps) as progress:
            for filename in commands:
                load_deploy_file(state, filename, progress=progress)
                progress()

    # Operation w/optional args
    elif command == 'op':
        print()
        print('--> Preparing operation...')

        op, args = commands

        add_op(
            state, op,
            *args[0], **args[1]
        )

    # Always show meta output
    print()
    print('--> Proposed changes:')
    print_meta(state, inventory)

    # If --debug-state, dump state (ops, op order, op meta) now & exit
    if debug_state:
        dump_state(state)
        _exit()

    # Run the operations we generated with the deploy file
    if dry:
        _exit()

    print()

    # Run the before_deploy hook if provided
    run_hook(state, 'before_deploy', hook_data)

    print('--> Beginning operation run...')

    # Number of "steps" to make = number of operations * number of hosts
    operation_steps = len(state.op_order) * len(state.inventory)
    with progress_spinner(operation_steps) as progress:
        run_ops(
            state,
            serial=serial,
            no_wait=no_wait,
            progress=progress,
        )

    # Run the after_deploy hook if provided
    run_hook(state, 'after_deploy', hook_data)

    print('--> Results:')
    print_results(state, inventory)

    _exit()
