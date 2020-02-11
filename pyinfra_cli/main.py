from __future__ import division, print_function

import logging
import sys
import warnings

from fnmatch import fnmatch
from os import getcwd, path

import click

from pyinfra import (
    __version__,
    logger,
    pseudo_inventory,
    pseudo_state,
)
from pyinfra.api import State
from pyinfra.api.connect import connect_all, disconnect_all
from pyinfra.api.exceptions import NoGroupError, PyinfraError
from pyinfra.api.facts import (
    get_fact_class,
    get_fact_names,
    get_facts,
    is_fact,
    ShortFactBase,
)
from pyinfra.api.operation import add_op
from pyinfra.api.operations import run_ops
from pyinfra.api.util import FallbackDict
from pyinfra.modules import server

from .config import load_config, load_deploy_config
from .exceptions import CliError, UnexpectedError
from .inventory import make_inventory
from .log import setup_logging
from .prints import (
    print_facts,
    print_facts_list,
    print_inventory,
    print_meta,
    print_operations_list,
    print_results,
    print_state_facts,
    print_state_operations,
    print_support_info,
)
from .util import (
    get_operation_and_args,
    load_deploy_file,
    run_hook,
)
from .virtualenv import init_virtualenv


# Exit handler
def _exit():
    if pseudo_state.isset() and pseudo_state.failed_hosts:
        sys.exit(1)
    sys.exit(0)


def _print_facts(ctx, param, value):
    if not value:
        return

    click.echo('--> Available facts:')
    print_facts_list()
    ctx.exit()


def _print_operations(ctx, param, value):
    if not value:
        return

    click.echo('--> Available operations:')
    print_operations_list()
    ctx.exit()


def _print_support(ctx, param, value):
    if not value:
        return

    click.echo('--> Support information:')
    print_support_info()
    ctx.exit()


@click.command()
@click.argument('inventory', nargs=1)
@click.argument('operations', nargs=-1, required=True)
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
    help="Don't execute operations on the target hosts.",
)
@click.option(
    '--limit',
    help='Restrict the target hosts by name and group name.',
)
@click.option(
    '--no-wait', is_flag=True, default=False,
    help="Don't wait between operations for hosts to complete.",
)
@click.option(
    '--serial', is_flag=True, default=False,
    help='Run operations in serial, host by host.',
)
@click.option(
    '--quiet', is_flag=True, default=False,
    help='Hide most pyinfra output',
)
# Eager commands (pyinfra [--facts | --operations | --support | --version])
@click.option(
    '--facts', is_flag=True, is_eager=True, callback=_print_facts,
    help='Print available facts list and exit.',
)
@click.option(
    'print_operations', '--operations',
    is_flag=True,
    is_eager=True,
    callback=_print_operations,
    help='Print available operations list and exit.',
)
@click.option(
    '--support', is_flag=True, is_eager=True, callback=_print_support,
    help='Print useful information for support and exit.',
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

    # OPERATIONS

    \b
    # Run one or more deploys against the inventory
    pyinfra INVENTORY deploy_web.py [deploy_db.py]...

    \b
    # Run a single operation against the inventory
    pyinfra INVENTORY server.user pyinfra home=/home/pyinfra

    \b
    # Execute an arbitrary command on the inventory
    pyinfra INVENTORY exec -- echo "hello world"

    \b
    # Run one or more facts on the inventory
    pyinfra INVENTORY fact linux_distribution [users]...
    pyinfra INVENTORY all-facts
    '''

    main(*args, **kwargs)


# This is a hack around Click 7 not being released (like, forever) which has the
# magical click.option(hidden=True) capability.
if '--help' not in sys.argv:
    extra_options = (
        click.option(
            '--debug', is_flag=True, default=False,
            help='Print debug info.',
        ),
        click.option(
            '--debug-data', is_flag=True, default=False,
            help='Print host/group data before connecting and exit.',
        ),
        click.option(
            '--debug-facts', is_flag=True, default=False,
            help='Print facts after generating operations and exit.',
        ),
        click.option(
            '--debug-operations', is_flag=True, default=False,
            help='Print operations after generating and exit.',
        ),
    )

    for decorator in extra_options:
        cli = decorator(cli)


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

    except Exception as e:
        # Attach the traceback to the exception before returning as state (Py2
        # does not have `Exception.__traceback__`).
        _, _, traceback = sys.exc_info()
        e._traceback = traceback

        # Re-raise any unexpected exceptions as UnexpectedError
        raise UnexpectedError(e)

    finally:
        if pseudo_state.isset() and pseudo_state.initialised:
            # Triggers any executor disconnect requirements
            disconnect_all(pseudo_state)


def _main(
    inventory, operations, verbosity,
    user, port, key, key_password, password,
    sudo, sudo_user, su_user,
    parallel, fail_percent,
    dry, limit, no_wait, serial, quiet,
    debug, debug_data, debug_facts, debug_operations,
    facts=None, print_operations=None, support=None,
):
    if not debug and not sys.warnoptions:
        warnings.simplefilter('ignore')

    # Setup logging
    log_level = logging.INFO
    if debug:
        log_level = logging.DEBUG
    elif quiet:
        log_level = logging.WARNING

    setup_logging(log_level)

    # Bootstrap any virtualenv
    init_virtualenv()

    deploy_dir = getcwd()
    potential_deploy_dirs = []

    # This is the most common case: we have a deploy file so use it's
    # pathname - we only look at the first file as we can't have multiple
    # deploy directories.
    if operations[0].endswith('.py'):
        deploy_file_dir, _ = path.split(operations[0])
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

    # Debug (print) inventory + group data
    if operations[0] == 'debug-inventory':
        command = 'debug-inventory'

    # Get all non-arg facts
    elif operations[0] == 'all-facts':
        command = 'fact'
        fact_names = []

        for fact_name in get_fact_names():
            fact_class = get_fact_class(fact_name)
            if (
                not issubclass(fact_class, ShortFactBase)
                and not callable(fact_class.command)
            ):
                fact_names.append(fact_name)

        operations = [(name, None) for name in fact_names]

    # Get one or more facts
    elif operations[0] == 'fact':
        command = 'fact'

        fact_names = operations[1:]
        facts = []

        for name in fact_names:
            args = None

            if ':' in name:
                name, args = name.split(':', 1)
                args = args.split(',')

            if not is_fact(name):
                raise CliError('No fact: {0}'.format(name))

            facts.append((name, args))

        operations = facts

    # Execute a raw command with server.shell
    elif operations[0] == 'exec':
        command = 'exec'
        operations = operations[1:]

    # Execute one or more deploy files
    elif all(cmd.endswith('.py') for cmd in operations):
        command = 'deploy'
        operations = operations[0:]

        for file in operations:
            if not path.exists(file):
                raise CliError('No deploy file: {0}'.format(file))

    # Operation w/optional args (<module>.<op> ARG1 ARG2 ...)
    elif len(operations[0].split('.')) == 2:
        command = 'op'
        operations = get_operation_and_args(operations)

    else:
        raise CliError('''Invalid operations: {0}

    Operation usage:
    pyinfra INVENTORY deploy_web.py [deploy_db.py]...
    pyinfra INVENTORY server.user pyinfra home=/home/pyinfra
    pyinfra INVENTORY exec -- echo "hello world"
    pyinfra INVENTORY fact os [users]...'''.format(operations))

    # Create an empty/unitialised state object
    state = State()
    pseudo_state.set(state)

    # Setup printing on the new state
    print_operation_io = verbosity > 0
    print_fact_io = verbosity > 1

    state.print_output = print_operation_io  # -v
    state.print_input = print_operation_io  # -v
    state.print_fact_info = print_operation_io  # -v

    state.print_fact_output = print_fact_io  # -vv
    state.print_fact_input = print_fact_io  # -vv

    if not quiet:
        click.echo('--> Loading config...')

    # Load up any config.py from the filesystem
    config = load_config(deploy_dir)

    # Load any hooks/config from the deploy file
    if command == 'deploy':
        load_deploy_config(operations[0], config)

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

    if not quiet:
        click.echo('--> Loading inventory...')

    # Load up the inventory from the filesystem
    inventory, inventory_group = make_inventory(
        inventory,
        deploy_dir=deploy_dir,
        ssh_port=port,
        ssh_user=user,
        ssh_key=key,
        ssh_key_password=key_password,
        ssh_password=password,
    )

    # Apply any --limit to the inventory
    limit_hosts = None

    if limit:
        try:
            limit_hosts = inventory.get_group(limit)
        except NoGroupError:
            limits = limit.split(',')

            limit_hosts = [
                host for host in inventory
                if any(fnmatch(host.name, limit) for limit in limits)
            ]

    # Attach to pseudo inventory
    pseudo_inventory.set(inventory)

    # Initialise the state, passing any initial --limit
    state.init(inventory, config, initial_limit=limit_hosts)

    # If --debug-data dump & exit
    if command == 'debug-inventory' or debug_data:
        if debug_data:
            logger.warning((
                '--debug-data is deprecated, '
                'please use `pyinfra INVENTORY debug-inventory` instead.'
            ))
        print_inventory(state)
        _exit()

    # Set the deploy directory
    state.deploy_dir = deploy_dir

    # Setup the data to be passed to config hooks
    hook_data = FallbackDict(
        state.inventory.get_override_data(),
        state.inventory.get_group_data(inventory_group),
        state.inventory.get_data(),
    )

    # Run the before_connect hook if provided
    run_hook(state, 'before_connect', hook_data)

    # Connect to all the servers
    if not quiet:
        click.echo()
        click.echo('--> Connecting to hosts...')
    connect_all(state)

    # Run the before_connect hook if provided
    run_hook(state, 'before_facts', hook_data)

    # Just getting a fact?
    #

    if command == 'fact':
        if not quiet:
            click.echo()
            click.echo('--> Gathering facts...')

        # Print facts as we get them
        state.print_fact_info = True

        # Print fact output with -v
        state.print_fact_output = print_operation_io
        state.print_fact_input = print_operation_io

        fact_data = {}

        for i, command in enumerate(operations):
            name, args = command
            fact_data[name] = get_facts(
                state, name,
                args=args,
            )

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
            ' '.join(operations),
        )

    # Deploy files(s)
    elif command == 'deploy':
        if not quiet:
            click.echo()
            click.echo('--> Preparing operations...')

        # Number of "steps" to make = number of files * number of hosts
        for i, filename in enumerate(operations):
            logger.info('Loading: {0}'.format(click.style(filename, bold=True)))
            state.current_op_file = i
            load_deploy_file(state, filename)

    # Operation w/optional args
    elif command == 'op':
        if not quiet:
            click.echo()
            click.echo('--> Preparing operation...')

        op, args = operations

        add_op(
            state, op,
            *args[0], **args[1]
        )

    # Always show meta output
    if not quiet:
        click.echo()
        click.echo('--> Proposed changes:')
    print_meta(state)

    # If --debug-facts or --debug-operations, print and exit
    if debug_facts or debug_operations:
        if debug_facts:
            print_state_facts(state)

        if debug_operations:
            print_state_operations(state)

        _exit()

    # Run the operations we generated with the deploy file
    if dry:
        _exit()

    if not quiet:
        click.echo()

    # Run the before_deploy hook if provided
    run_hook(state, 'before_deploy', hook_data)

    if not quiet:
        click.echo('--> Beginning operation run...')
    run_ops(state, serial=serial, no_wait=no_wait)

    # Run the after_deploy hook if provided
    run_hook(state, 'after_deploy', hook_data)

    if not quiet:
        click.echo('--> Results:')
    print_results(state)

    _exit()
