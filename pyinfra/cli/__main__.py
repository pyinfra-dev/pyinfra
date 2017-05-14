#!/usr/bin/env python
# pyinfra
# File: bin/pyinfra
# Desc: the CLI in front of the API

from __future__ import division, print_function, unicode_literals

import logging
import signal
import sys

from os import getcwd, path

import click

from colorama import init as colorama_init

from pyinfra import (
    __version__,
    hook,
    logger,
    pseudo_host,
    pseudo_inventory,
    pseudo_state,
)

from pyinfra.api import State
from pyinfra.api.attrs import FallbackAttrData
from pyinfra.api.exceptions import PyinfraError
from pyinfra.api.facts import get_facts, is_fact
from pyinfra.api.operation import add_op
from pyinfra.api.operations import run_ops
from pyinfra.api.ssh import connect_all

from pyinfra.modules import server

from . import CliError, run_hook
from .commands import get_operation_and_args, load_deploy_file
from .config import load_config, load_deploy_config
from .fake import FakeHost, FakeInventory, FakeState
from .inventory import make_inventory
from .legacy import run_main_with_legacy_arguments
from .log import print_blank, setup_logging
from .prints import (
    dump_state,
    dump_trace,
    print_facts,
    print_facts_list,
    print_inventory,
    print_meta,
    print_results,
)


# Init colorama for Windows ANSI color support
colorama_init()

# Don't write out deploy.pyc/config.pyc etc
sys.dont_write_bytecode = True

# Make sure imported files (deploy.py/etc) behave as if imported from the cwd
sys.path.append('.')

# Shut it click
click.disable_unicode_literals_warning = True  # noqa


# Handle ctrl+c
def _signal_handler(signum, frame):
    print('Exiting upon user request!')
    sys.exit(0)


signal.signal(signal.SIGINT, _signal_handler)


# Exit handler
def _exit(code=0):
    print_blank()
    print('<-- Thank you, goodbye')
    print_blank()

    sys.exit(code)


# Exception handler
def _exception(name, e, dump=False):
    if pseudo_host.isset():
        sys.stderr.write('--> [{0}]: {1}: '.format(
            click.style(pseudo_host.name, bold=True),
            click.style(name, 'red', bold=True),
        ))
    else:
        sys.stderr.write('--> {0}: '.format(click.style(name, 'red', bold=True)))

    if e:
        logger.warning(e)

    if dump:
        dump_trace(sys.exc_info())

    _exit(1)


def _print_facts(ctx, param, value):
    if not value:
        return

    print('--> Available facts:')
    print_facts_list()
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
    '--enable-pipelining', is_flag=True, default=False,
    help='Enable pipelining [EXPERIMENTAL].',
)
@click.option(
    '--facts', is_flag=True, is_eager=True, callback=_print_facts,
    help='Print available facts list and exit.',
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


def main(
    inventory, commands, verbosity,
    user, port, key, key_password, password,
    sudo, sudo_user, su_user,
    parallel, fail_percent,
    dry, limit, no_wait, serial,
    debug, debug_data, debug_state,
    enable_pipelining,
    facts=None,
):
    print_blank()
    print('### {0}'.format(click.style('Welcome to pyinfra', bold=True)))
    print_blank()

    # Setup logging
    log_level = logging.DEBUG if debug else logging.INFO
    setup_logging(log_level)

    try:
        print('--> Loading inventory...')

        deploy_dir = getcwd()

        # This is the most common case: we have a deploy file so use it's
        # pathname - we only look at the first file as we can't have multiple
        # deploy directories.
        if commands[0].endswith('.py'):
            deploy_dir = path.dirname(commands[0])

        # If we have a valid inventory, look in it's path and it's parent for
        # group_data or config.py to indicate deploy_dir (--fact, --run).
        elif inventory.endswith('.py') and path.isfile(inventory):
            inventory_dir, _ = path.split(inventory)
            above_inventory_dir, _ = path.split(inventory_dir)

            for inventory_path in (inventory_dir, above_inventory_dir):
                if any((
                    path.isdir(path.join(inventory_path, 'group_data')),
                    path.isfile(path.join(inventory_path, 'config.py')),
                )):
                    deploy_dir = inventory_path

        # Set a fake state/host/inventory
        pseudo_state.set(FakeState())
        pseudo_host.set(FakeHost())
        pseudo_inventory.set(FakeInventory())

        # Load up any config.py from the filesystem
        config = load_config(deploy_dir)

        # Load any hooks/config from the deploy file
        if commands[0].endswith('.py'):
            load_deploy_config(commands[0], config)

        # Unset fake state/host/inventory
        pseudo_host.reset()
        pseudo_state.reset()
        pseudo_inventory.reset()

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
        connect_all(state)

        # Run the before_connect hook if provided
        run_hook(state, 'before_facts', hook_data)

        # Just getting a fact?
        #

        if commands[0] == 'fact':
            print_blank()
            print('--> Gathering facts...')

            # Print facts as we get them
            state.print_fact_info = True

            # Print fact output with -v
            state.print_fact_output = print_output

            fact_names = commands[1:]
            facts = []

            for name in fact_names:
                args = None

                if ':' in name:
                    name, args = name.split(':', 1)
                    args = args.split(',')

                if not is_fact(name):
                    raise CliError('Invalid fact: {0}'.format(name))

                facts.append((name, args))

            fact_data = {}

            for name, args in facts:
                fact_data[name] = get_facts(
                    state, name,
                    args=args,
                    sudo=sudo,
                    sudo_user=sudo_user,
                    su_user=su_user,
                )

            print_facts(fact_data)
            _exit()

        # Prepare the deploy!
        #

        # Execute a raw command with server.shell
        if commands[0] == 'exec':
            # Print the output of the command
            state.print_output = True

            add_op(
                state, server.shell,
                ' '.join(commands[1:]),
            )

        # Deploy files(s)
        elif all(command.endswith('.py') for command in commands):
            print_blank()
            print('--> Preparing operations...')

            for filename in commands:
                if enable_pipelining:
                    with state.pipeline_facts:
                        load_deploy_file(state, filename)

                else:
                    load_deploy_file(state, filename)

        # Operation w/optional args
        elif len(commands) == 2:
            print_blank()
            print('--> Preparing operation...')

            op, args = get_operation_and_args(
                commands[0], commands[1],
            )

            add_op(
                state, op,
                *args[0], **args[1]
            )

        else:
            raise CliError('''Invalid commands: {0}

    Command usage:
    pyinfra INVENTORY deploy_web.py [deploy_db.py]...
    pyinfra INVENTORY server.user pyinfra,home=/home/pyinfra
    pyinfra INVENTORY exec -- echo "hello world"
    pyinfra INVENTORY fact os [users]...'''.format(commands))

        # Always show meta output
        print_blank()
        print('--> Proposed changes:')
        print_meta(state, inventory)

        # If --debug-state, dump state (ops, op order, op meta) now & exit
        if debug_state:
            dump_state(state)
            _exit()

        # Run the operations we generated with the deploy file
        if dry:
            _exit()

        print_blank()

        # Run the before_deploy hook if provided
        run_hook(state, 'before_deploy', hook_data)

        print('--> Beginning operation run...')
        run_ops(
            state,
            serial=serial,
            no_wait=no_wait,
        )

        # Run the after_deploy hook if provided
        run_hook(state, 'after_deploy', hook_data)

        print('--> Results:')
        print_results(state, inventory)

    # Hook errors
    except hook.Error as e:
        _exception('hook error', e, dump=debug)

    # Internal exceptions
    except PyinfraError as e:
        _exception('pyinfra error', e, dump=debug)

    # IO errors
    except IOError as e:
        _exception('local IO error', e, dump=debug)

    # Unexpected exceptions/everything else
    except Exception as e:
        _exception('unknown error', e, dump=True)

    _exit()


# TODO: Explain this!
if '-i' in sys.argv:
    run_main_with_legacy_arguments(main)
else:
    cli()
