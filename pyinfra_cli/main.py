import logging
import sys
import warnings
from fnmatch import fnmatch
from os import chdir as os_chdir, getcwd, path
from typing import Iterable, List, Tuple, Union

import click

from pyinfra import __version__, logger, state
from pyinfra.api import Config, State
from pyinfra.api.connect import connect_all, disconnect_all
from pyinfra.api.exceptions import NoGroupError, PyinfraError
from pyinfra.api.facts import get_facts
from pyinfra.api.operations import run_ops
from pyinfra.api.util import get_kwargs_str
from pyinfra.context import ctx_config, ctx_inventory, ctx_state
from pyinfra.operations import server

from .commands import get_facts_and_args, get_func_and_args
from .exceptions import CliError, UnexpectedExternalError, UnexpectedInternalError
from .inventory import make_inventory
from .log import setup_logging
from .prints import (
    print_facts,
    print_inventory,
    print_meta,
    print_results,
    print_state_facts,
    print_state_operations,
    print_support_info,
)
from .util import exec_file, load_deploy_file, load_func, parse_cli_arg
from .virtualenv import init_virtualenv


def _exit():
    if ctx_state.isset() and state.failed_hosts:
        sys.exit(1)
    sys.exit(0)


def _print_support(ctx, param, value):
    if not value:
        return

    click.echo("--> Support information:", err=True)
    print_support_info()
    ctx.exit()


@click.command()
@click.argument("inventory", nargs=1, type=click.Path(exists=False))
@click.argument("operations", nargs=-1, required=True, type=click.Path(exists=False))
@click.option(
    "verbosity",
    "-v",
    count=True,
    help="Print meta (-v), input (-vv) and output (-vvv).",
)
@click.option(
    "--dry",
    is_flag=True,
    default=False,
    help="Don't execute operations on the target hosts.",
)
@click.option(
    "--limit",
    help="Restrict the target hosts by name and group name.",
    multiple=True,
)
@click.option("--fail-percent", type=int, help="% of hosts that need to fail before exiting early.")
@click.option(
    "--data",
    multiple=True,
    help="Override data values, format key=value.",
)
@click.option(
    "--group-data",
    multiple=True,
    help="Paths to load additional group data from (overrides matching keys).",
)
@click.option(
    "--config",
    "config_filename",
    help="Specify config file to use (default: config.py).",
    default="config.py",
)
@click.option(
    "--chdir",
    help="Set the working directory before executing.",
)
# Auth args
@click.option(
    "--sudo",
    is_flag=True,
    default=False,
    help="Whether to execute operations with sudo.",
)
@click.option("--sudo-user", help="Which user to sudo when sudoing.")
@click.option(
    "--use-sudo-password",
    is_flag=True,
    default=False,
    help="Whether to use a password with sudo.",
)
@click.option("--su-user", help="Which user to su to.")
@click.option("--shell-executable", help='Shell to use (ex: "sh", "cmd", "ps").')
# Operation flow args
@click.option("--parallel", type=int, help="Number of operations to run in parallel.")
@click.option(
    "--no-wait",
    is_flag=True,
    default=False,
    help="Don't wait between operations for hosts.",
)
@click.option(
    "--serial",
    is_flag=True,
    default=False,
    help="Run operations in serial, host by host.",
)
# SSH connector args
# TODO: remove the non-ssh-prefixed variants
@click.option("--ssh-user", "--user", "ssh_user", help="SSH user to connect as.")
@click.option("--ssh-port", "--port", "ssh_port", type=int, help="SSH port to connect to.")
@click.option("--ssh-key", "--key", "ssh_key", type=click.Path(), help="SSH Private key filename.")
@click.option(
    "--ssh-key-password",
    "--key-password",
    "ssh_key_password",
    help="SSH Private key password.",
)
@click.option("--ssh-password", "--password", "ssh_password", help="SSH password.")
# WinRM connector args
@click.option("--winrm-username", help="WINRM user to connect as.")
@click.option("--winrm-password", help="WINRM password.")
@click.option("--winrm-port", help="WINRM port to connect to.")
@click.option("--winrm-transport", help="WINRM transport for use.")
# Eager commands (pyinfra --support)
@click.option(
    "--support",
    is_flag=True,
    is_eager=True,
    callback=_print_support,
    help="Print useful information for support and exit.",
)
# Debug args
@click.option(
    "--quiet",
    is_flag=True,
    default=False,
    help="Hide most pyinfra output.",
)
@click.option(
    "--debug",
    is_flag=True,
    default=False,
    help="Print debug info.",
)
@click.option(
    "--debug-facts",
    is_flag=True,
    default=False,
    help="Print facts after generating operations and exit.",
)
@click.option(
    "--debug-operations",
    is_flag=True,
    default=False,
    help="Print operations after generating and exit.",
)
@click.version_option(
    version=__version__,
    prog_name="pyinfra",
    message="%(prog)s: v%(version)s",
)
def cli(*args, **kwargs):
    """
    pyinfra manages the state of one or more servers. It can be used for
    app/service deployment, config management and ad-hoc command execution.

    Documentation: docs.pyinfra.com

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
    # Execute an arbitrary command against the inventory
    pyinfra INVENTORY exec -- echo "hello world"

    \b
    # Run one or more facts against the inventory
    pyinfra INVENTORY fact server.LinuxName [server.Users]...
    pyinfra INVENTORY fact files.File path=/path/to/file...

    \b
    # Debug the inventory hosts and data
    pyinfra INVENTORY debug-inventory
    """

    try:
        _main(*args, **kwargs)

    except PyinfraError as e:
        # Re-raise any internal exceptions that aren't handled by click as
        # CliErrors which are.
        if not isinstance(e, click.ClickException):
            message = getattr(e, "message", e.args[0])
            raise CliError(message)

        raise

    except UnexpectedExternalError:
        # Pass unexpected external exceptions through as-is
        raise

    except Exception as e:
        # Re-raise any unexpected internal exceptions as UnexpectedInternalError
        raise UnexpectedInternalError(e)

    finally:
        if ctx_state.isset() and state.initialised:
            # Triggers any executor disconnect requirements
            disconnect_all(state)


class CliCommands:
    DEBUG_INVENTORY = "DEBUG_INVENTORY"
    FACT = "FACT"
    SHELL = "SHELL"
    DEPLOY_FILES = "DEPLOY_FILES"
    FUNC = "FUNC"


def _main(
    inventory,
    operations: Union[List, Tuple],
    verbosity: int,
    chdir: str,
    ssh_user,
    ssh_port: int,
    ssh_key,
    ssh_key_password: str,
    ssh_password: str,
    winrm_username: str,
    winrm_password: str,
    winrm_port,
    winrm_transport,
    shell_executable,
    sudo: bool,
    sudo_user: str,
    use_sudo_password: bool,
    su_user: str,
    parallel: int,
    fail_percent: int,
    data,
    group_data,
    config_filename: str,
    dry: bool,
    limit: Iterable,
    no_wait: bool,
    serial: bool,
    quiet: bool,
    debug: bool,
    debug_facts: bool,
    debug_operations: bool,
    support: bool = None,
):
    # Setup working directory
    #
    if chdir:
        os_chdir(chdir)

    # Setup logging & Bootstrap/Venv
    #
    _setup_log_level(debug, quiet)
    init_virtualenv()

    # Check operations are valid and setup commands
    #
    original_operations, operations, command, chdir = _validate_operations(operations, chdir)

    # Setup state, config & inventory
    #
    state = _setup_state(verbosity, quiet)
    config = Config()
    ctx_config.set(config)

    # Update Config & Override Data
    #
    config = _set_config(
        config,
        config_filename,
        sudo,
        sudo_user,
        use_sudo_password,
        su_user,
        parallel,
        shell_executable,
        fail_percent,
        quiet,
    )
    override_data = _set_override_data(
        data,
        ssh_user,
        ssh_key,
        ssh_key_password,
        ssh_port,
        ssh_password,
        winrm_username,
        winrm_password,
        winrm_port,
        winrm_transport,
    )

    # Load up the inventory from the filesystem
    #
    echo_msg("--> Loading inventory...", quiet)
    inventory = make_inventory(
        inventory,
        cwd=state.cwd,
        override_data=override_data,
        group_data_directories=group_data,
    )
    ctx_inventory.set(inventory)

    # Now that we have inventory, apply --limit config override
    initial_limit = _apply_inventory_limit(inventory, limit)

    # Initialise the state
    state.init(inventory, config, initial_limit=initial_limit)

    if command == CliCommands.DEBUG_INVENTORY:
        print_inventory(state)
        _exit()

    # Connect to the hosts & start handling the user commands
    #
    echo_msg("--> Connecting to hosts...", quiet)
    connect_all(state)
    state, config = _handle_commands(state, config, command, original_operations, operations, quiet)

    # Print proposed changes, execute unless --dry, and exit
    #
    echo_msg("--> Proposed changes:", quiet)
    print_meta(state)

    # If --debug-facts or --debug-operations, print and exit
    if debug_facts or debug_operations:
        if debug_facts:
            print_state_facts(state)

        if debug_operations:
            print_state_operations(state)

        _exit()

    if dry:
        _exit()

    echo_msg(quiet=quiet)
    echo_msg("--> Beginning operation run...", quiet)

    run_ops(state, serial=serial, no_wait=no_wait)

    echo_msg("--> Results:", quiet)
    print_results(state)
    _exit()


# Setup
#
def _setup_log_level(debug, quiet):
    if not debug and not sys.warnoptions:
        warnings.simplefilter("ignore")

    log_level = logging.INFO
    if debug:
        log_level = logging.DEBUG
    elif quiet:
        log_level = logging.WARNING

    setup_logging(log_level)


def _validate_operations(operations, chdir):

    # Make a copy before we overwrite
    original_operations = operations

    # Debug (print) inventory + group data
    if operations[0] == "debug-inventory":
        command = CliCommands.DEBUG_INVENTORY

    # Get one or more facts
    elif operations[0] == "fact":
        command = CliCommands.FACT
        operations = get_facts_and_args(operations[1:])

    # Execute a raw command with server.shell
    elif operations[0] == "exec":
        command = CliCommands.SHELL
        operations = operations[1:]

    # Execute one or more deploy files
    elif all(cmd.endswith(".py") for cmd in operations):
        command = CliCommands.DEPLOY_FILES

        filenames = []

        for filename in operations[0:]:
            if path.exists(filename):
                filenames.append(filename)
                continue
            if chdir and filename.startswith(chdir):
                correct_filename = path.relpath(filename, chdir)
                logger.warning(
                    (
                        "Fixing deploy filename under `--chdir` argument: "
                        f"{filename} -> {correct_filename}"
                    ),
                )
                filenames.append(correct_filename)
                continue
            raise CliError(
                "No deploy file: {0}".format(
                    path.join(chdir, filename) if chdir else filename,
                ),
            )

        operations = filenames

    # Load a function (op or deploy) directly with arguments
    elif "." in operations[0]:
        command = CliCommands.FUNC
        operations = get_func_and_args(operations)

    else:
        raise CliError(
            """Invalid operations: {0}

    Operation usage:
    pyinfra INVENTORY deploy_web.py [deploy_db.py]...
    pyinfra INVENTORY server.user pyinfra home=/home/pyinfra
    pyinfra INVENTORY exec -- echo "hello world"
    pyinfra INVENTORY fact os [users]...""".format(
                operations,
            ),
        )

    return original_operations, operations, command, chdir


def _set_verbosity(state, verbosity, quiet):
    if verbosity > 0:
        state.print_fact_info = True
        state.print_noop_info = True

    if verbosity > 1:
        state.print_input = state.print_fact_input = True

    if verbosity > 2:
        state.print_output = state.print_fact_output = True

    return state


def _setup_state(verbosity, quiet):
    cwd = getcwd()
    if cwd not in sys.path:  # ensure cwd is present in sys.path
        sys.path.append(cwd)

    state = State()
    state.cwd = cwd
    ctx_state.set(state)

    state = _set_verbosity(state, verbosity, quiet)
    return state


def _set_config(
    config,
    config_filename,
    sudo,
    sudo_user,
    use_sudo_password,
    su_user,
    parallel,
    shell_executable,
    fail_percent,
    quiet,
):
    echo_msg("--> Loading config...", quiet)

    # Load up any config.py from the filesystem
    config_filename = path.join(state.cwd, config_filename)
    if path.exists(config_filename):
        exec_file(config_filename)

    # Lock the current config, this allows us to restore this version after
    # executing deploy files that may alter them.
    config.lock_current_state()

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
        config.SHELL = None if shell_executable in ("None", "null") else shell_executable

    if fail_percent is not None:
        config.FAIL_PERCENT = fail_percent

    return config


def _set_override_data(
    data,
    ssh_user,
    ssh_key,
    ssh_key_password,
    ssh_port,
    ssh_password,
    winrm_username,
    winrm_password,
    winrm_port,
    winrm_transport,
):
    override_data = {}

    for arg in data:
        key, value = arg.split("=", 1)
        override_data[key] = value

    override_data = {key: parse_cli_arg(value) for key, value in override_data.items()}

    for key, value in (
        ("ssh_user", ssh_user),
        ("ssh_key", ssh_key),
        ("ssh_key_password", ssh_key_password),
        ("ssh_port", ssh_port),
        ("ssh_password", ssh_password),
        ("winrm_username", winrm_username),
        ("winrm_password", winrm_password),
        ("winrm_port", winrm_port),
        ("winrm_transport", winrm_transport),
    ):
        if value:
            override_data[key] = value

    return override_data


def _apply_inventory_limit(inventory, limit):
    initial_limit = None
    if limit:
        all_limit_hosts = []

        for limiter in limit:
            try:
                limit_hosts = inventory.get_group(limiter)
            except NoGroupError:
                limit_hosts = [host for host in inventory if fnmatch(host.name, limiter)]

            if not limit_hosts:
                logger.warning("No host matches found for --limit pattern: {0}".format(limiter))

            all_limit_hosts.extend(limit_hosts)
        initial_limit = list(set(all_limit_hosts))

    return initial_limit


# Operations Execution
#
def _handle_commands(state, config, command, original_operations, operations, quiet):

    if command is CliCommands.FACT:
        state, fact_data = _run_fact_operations(state, config, operations, quiet)
        print_facts(fact_data)
        _exit()

    if command == CliCommands.SHELL:
        state = _run_exec_operations(state, config, operations, quiet)

    elif command == CliCommands.DEPLOY_FILES:
        state, config, operations = _run_deploy_operations(state, config, operations, quiet)

    elif command == CliCommands.FUNC:
        state, kwargs = _run_func_operations(state, config, operations, original_operations, quiet)

    return state, config


def _run_fact_operations(state, config, operations, quiet):
    echo_msg("--> Gathering facts...", quiet)

    state.print_fact_info = True
    fact_data = {}

    for i, command in enumerate(operations):
        fact_cls, args, kwargs = command
        fact_key = fact_cls.name

        if args or kwargs:
            _fact_args = args or ""
            _fact_details = " ({0})".format(get_kwargs_str(kwargs)) if kwargs else ""
            fact_key = "{0}{1}{2}".format(fact_cls.name, _fact_args, _fact_details)

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

    return state, fact_data


def _run_exec_operations(state, config, operations, quiet):
    state.print_output = True
    load_func(
        state,
        server.shell,
        " ".join(operations),
    )
    return state


def _run_deploy_operations(state, config, operations, quiet):
    echo_msg("--> Preparing Operations...", quiet)

    # Number of "steps" to make = number of files * number of hosts
    for i, filename in enumerate(operations):
        _log_styled_msg = click.style(filename, bold=True)
        logger.info("Loading: {0}".format(_log_styled_msg))

        state.current_op_file_number = i
        load_deploy_file(state, filename)

        # Remove any config changes introduced by the deploy file & any includes
        config.reset_locked_state()

    return state, config, operations


def _run_func_operations(state, config, operations, original_operations, quiet):
    echo_msg("--> Preparing operation...", quiet)

    op, args = operations
    args, kwargs = args

    load_func(state, op, *args, **kwargs)

    return state, kwargs


# Utils
#
def echo_msg(msg=None, quiet=None):
    if not quiet:
        click.echo(err=True)
    if msg:
        click.echo(msg, err=True)
