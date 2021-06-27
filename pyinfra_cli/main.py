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
    ShortFactBase,
)
from pyinfra.api.operation import add_op
from pyinfra.api.operations import run_ops
from pyinfra.api.util import get_kwargs_str
from pyinfra.operations import server

from .config import load_config, load_deploy_config
from .exceptions import (
    CliError,
    UnexpectedExternalError,
    UnexpectedInternalError,
)
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
    get_facts_and_args,
    get_operation_and_args,
    list_dirs_above_file,
    load_deploy_file,
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

    click.echo(click.style(
        '--facts is deprecated and will be removed in the future.',
        'yellow',
    ), err=True)

    click.echo('--> Available facts:', err=True)
    print_facts_list()
    ctx.exit()


def _print_operations(ctx, param, value):
    if not value:
        return

    click.echo(click.style(
        '--operations is deprecated and will be removed in the future.',
        'yellow',
    ), err=True)
    click.echo('--> Available operations:', err=True)
    print_operations_list()
    ctx.exit()


def _print_support(ctx, param, value):
    if not value:
        return

    click.echo('--> Support information:', err=True)
    print_support_info()
    ctx.exit()


@click.command()
@click.argument('inventory', nargs=1)
@click.argument('operations', nargs=-1, required=True)
@click.option(
    'verbosity', '-v',
    count=True,
    help='Print meta (-v), input (-vv) and output (-vvv).',
)
@click.option(
    '--dry', is_flag=True, default=False,
    help="Don't execute operations on the target hosts.",
)
@click.option(
    '--limit',
    help='Restrict the target hosts by name and group name.',
    multiple=True,
)
@click.option('--fail-percent', type=int, help='% of hosts allowed to fail.')
# Auth args
@click.option(
    '--sudo', is_flag=True, default=False,
    help='Whether to execute operations with sudo.',
)
@click.option('--sudo-user', help='Which user to sudo when sudoing.')
@click.option(
    '--use-sudo-password', is_flag=True, default=False,
    help='Whether to use a password with sudo.',
)
@click.option('--su-user', help='Which user to su to.')
@click.option('--shell-executable', help='Shell to use (ex: "sh", "cmd", "ps").')
# Operation flow args
@click.option('--parallel', type=int, help='Number of operations to run in parallel.')
@click.option(
    '--no-wait', is_flag=True, default=False,
    help="Don't wait between operations for hosts.",
)
@click.option(
    '--serial', is_flag=True, default=False,
    help='Run operations in serial, host by host.',
)
# SSH connector args
# TODO: remove the non-ssh-prefixed variants
@click.option('--ssh-user', '--user', help='SSH user to connect as.')
@click.option('--ssh-port', '--port', type=int, help='SSH port to connect to.')
@click.option('--ssh-key', '--key', type=click.Path(), help='SSH Private key filename.')
@click.option('--ssh-key-password', '--key-password', help='SSH Private key password.')
@click.option('--ssh-password', '--password', help='SSH password.')
# WinRM connector args
@click.option('--winrm-username', help='WINRM user to connect as.')
@click.option('--winrm-password', help='WINRM password.')
@click.option('--winrm-port', help='WINRM port to connect to.')
@click.option('--winrm-transport', help='WINRM transport for use.')
# Eager commands (pyinfra --support)
@click.option(
    '--support', is_flag=True, is_eager=True, callback=_print_support,
    help='Print useful information for support and exit.',
)
# Debug args
@click.option(
    '--quiet', is_flag=True, default=False,
    help='Hide most pyinfra output.',
)
@click.option(
    '--debug', is_flag=True, default=False,
    help='Print debug info.',
)
@click.option(
    '--debug-facts', is_flag=True, default=False,
    help='Print facts after generating operations and exit.',
)
@click.option(
    '--debug-operations', is_flag=True, default=False,
    help='Print operations after generating and exit.',
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
    pyinfra INVENTORY fact server.LinuxName [server.Users]...
    pyinfra INVENTORY fact files.File path=/path/to/file...
    '''

    try:
        _main(*args, **kwargs)

    except PyinfraError as e:
        # Re-raise any internal exceptions that aren't handled by click as
        # CliErrors which are.
        if not isinstance(e, click.ClickException):
            message = getattr(e, 'message', e.args[0])
            raise CliError(message)

        raise

    except UnexpectedExternalError:
        # Pass unexpected external exceptions through as-is
        raise

    except Exception as e:
        # Re-raise any unexpected internal exceptions as UnexpectedInternalError
        raise UnexpectedInternalError(e)

    finally:
        if pseudo_state.isset() and pseudo_state.initialised:
            # Triggers any executor disconnect requirements
            disconnect_all(pseudo_state)


if '--help' not in sys.argv:
    click.option(
        '--facts', is_flag=True, is_eager=True, callback=_print_facts,
        help='Print available facts list and exit.',
    )(cli)
    click.option(
        'print_operations', '--operations',
        is_flag=True,
        is_eager=True,
        callback=_print_operations,
        help='Print available operations list and exit.',
    )(cli)
    click.option(
        '--debug-data', is_flag=True, default=False,
        help='Print host/group data before connecting and exit.',
    )(cli)


def _main(
    inventory, operations, verbosity,
    ssh_user, ssh_port, ssh_key, ssh_key_password, ssh_password,
    winrm_username, winrm_password, winrm_port,
    winrm_transport, shell_executable,
    sudo, sudo_user, use_sudo_password, su_user,
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

    cwd = getcwd()
    deploy_dir = cwd
    potential_deploy_dirs = []

    # This is the most common case: we have a deploy file so use it's
    # pathname - we only look at the first file as we can't have multiple
    # deploy directories.
    if operations[0].endswith('.py') and path.isfile(operations[0]):
        potential_deploy_dirs.extend(list_dirs_above_file(operations[0], cwd))

    # If we have a valid inventory, look in it's path and it's parent for
    # group_data or config.py to indicate deploy_dir (--fact, --run).
    if inventory.endswith('.py') and path.isfile(inventory):
        potential_deploy_dirs.extend([
            dirname for dirname in list_dirs_above_file(inventory, cwd)
            if dirname not in potential_deploy_dirs
        ])

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
    else:
        logger.debug('Deploy directory remains as cwd')

    # Make sure imported files (deploy.py/etc) behave as if imported from the cwd
    sys.path.append(deploy_dir)

    # Create an empty/unitialised state object
    state = State()
    # Set the deploy directory
    state.deploy_dir = deploy_dir

    pseudo_state.set(state)

    if verbosity > 0:
        state.print_fact_info = True
        state.print_noop_info = True

    if verbosity > 1:
        state.print_input = state.print_fact_input = True

    if verbosity > 2:
        state.print_output = state.print_fact_output = True

    if not quiet:
        click.echo('--> Loading config...', err=True)

    # Load up any config.py from the filesystem
    config = load_config(deploy_dir)

    # Make a copy before we overwrite
    original_operations = operations

    # Debug (print) inventory + group data
    if operations[0] == 'debug-inventory':
        command = 'debug-inventory'

    # Get all non-arg facts
    elif operations[0] == 'all-facts':
        click.echo(click.style(
            'all-facts is deprecated and will be removed in the future.',
            'yellow',
        ), err=True)

        command = 'fact'
        fact_ops = []

        for fact_name in get_fact_names():
            fact_class = get_fact_class(fact_name)
            if (
                not issubclass(fact_class, ShortFactBase)
                and not callable(fact_class.command)
            ):
                fact_ops.append((fact_class, None, None))

        operations = fact_ops

    # Get one or more facts
    elif operations[0] == 'fact':
        command = 'fact'
        operations = get_facts_and_args(operations[1:])

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

    # Load any hooks/config from the deploy file
    if command == 'deploy':
        load_deploy_config(operations[0], config)

    # Arg based config overrides
    if sudo:
        config.SUDO = True
        if sudo_user:
            config.SUDO_USER = sudo_user

    if use_sudo_password:
        config.USE_SUDO_PASSWORD = use_sudo_password

    if su_user:
        config.SU_USER = su_user

    if parallel:
        config.PARALLEL = parallel

    if shell_executable:
        config.SHELL = shell_executable

    if fail_percent is not None:
        config.FAIL_PERCENT = fail_percent

    if not quiet:
        click.echo('--> Loading inventory...', err=True)

    # Load up the inventory from the filesystem
    inventory, inventory_group = make_inventory(
        inventory,
        deploy_dir=deploy_dir,
        ssh_port=ssh_port,
        ssh_user=ssh_user,
        ssh_key=ssh_key,
        ssh_key_password=ssh_key_password,
        ssh_password=ssh_password,
        winrm_username=winrm_username,
        winrm_password=winrm_password,
        winrm_port=winrm_port,
        winrm_transport=winrm_transport,
    )

    # Attach to pseudo inventory
    pseudo_inventory.set(inventory)

    # Now that we have inventory, apply --limit config override
    initial_limit = None
    if limit:
        all_limit_hosts = []

        for limiter in limit:
            try:
                limit_hosts = inventory.get_group(limiter)
            except NoGroupError:
                limits = limiter.split(',')
                if len(limits) > 1:
                    logger.warning((
                        'Specifying comma separated --limit values is deprecated, '
                        'please use multiple --limit options.'
                    ))

                limit_hosts = [
                    host for host in inventory
                    if any(fnmatch(host.name, match) for match in limits)
                ]

            all_limit_hosts.extend(limit_hosts)

        initial_limit = list(set(all_limit_hosts))

    # Initialise the state
    state.init(inventory, config, initial_limit=initial_limit)

    # If --debug-data dump & exit
    if command == 'debug-inventory' or debug_data:
        if debug_data:
            logger.warning((
                '--debug-data is deprecated, '
                'please use `pyinfra INVENTORY debug-inventory` instead.'
            ))
        print_inventory(state)
        _exit()

    # Connect to all the servers
    if not quiet:
        click.echo(err=True)
        click.echo('--> Connecting to hosts...', err=True)
    connect_all(state)

    # Just getting a fact?
    #

    if command == 'fact':
        if not quiet:
            click.echo(err=True)
            click.echo('--> Gathering facts...', err=True)

        state.print_fact_info = True
        fact_data = {}

        for i, command in enumerate(operations):
            fact_cls, args, kwargs = command
            fact_key = fact_cls.name

            if args or kwargs:
                fact_key = '{0}{1}{2}'.format(
                    fact_cls.name,
                    args or '',
                    ' ({0})'.format(get_kwargs_str(kwargs)) if kwargs else '',
                )

            try:
                fact_data[fact_key] = get_facts(
                    state,
                    fact_cls,
                    args=args,
                    kwargs=kwargs,
                    apply_failed_hosts=False,
                )
            except PyinfraError:
                pass

        print_facts(fact_data)
        _exit()

    # Prepare the deploy!
    #

    # Execute a raw command with server.shell
    if command == 'exec':
        # Print the output of the command
        state.print_output = True

        add_op(
            state,
            server.shell,
            ' '.join(operations),
            _allow_cli_mode=True,
        )

    # Deploy files(s)
    elif command == 'deploy':
        if not quiet:
            click.echo(err=True)
            click.echo('--> Preparing operations...', err=True)

        # Number of "steps" to make = number of files * number of hosts
        for i, filename in enumerate(operations):
            logger.info('Loading: {0}'.format(click.style(filename, bold=True)))
            load_deploy_file(state, filename)

    # Operation w/optional args
    elif command == 'op':
        if not quiet:
            click.echo(err=True)
            click.echo('--> Preparing operation...', err=True)

        op, args = operations
        args, kwargs = args
        kwargs['_allow_cli_mode'] = True

        def print_host_ready(host):
            logger.info('{0}{1} {2}'.format(
                host.print_prefix,
                click.style('Ready:', 'green'),
                click.style(original_operations[0], bold=True),
            ))

        kwargs['_after_host_callback'] = print_host_ready

        add_op(state, op, *args, **kwargs)

    # Always show meta output
    if not quiet:
        click.echo(err=True)
        click.echo('--> Proposed changes:', err=True)
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
        click.echo(err=True)

    if not quiet:
        click.echo('--> Beginning operation run...', err=True)
    run_ops(state, serial=serial, no_wait=no_wait)

    if not quiet:
        click.echo('--> Results:', err=True)
    print_results(state)

    _exit()
