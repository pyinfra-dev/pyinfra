from os import path

import click

import pyinfra
from pyinfra import config, host, logger, state
from pyinfra.api.exceptions import PyinfraError
from pyinfra.api.util import get_file_path
from pyinfra.connectors.util import run_local_process, split_combined_output
from pyinfra.context import ctx_state


def include(filename: str):
    """
    Executes a local python file within the ``pyinfra.state.cwd``
    directory.
    """

    if not pyinfra.is_cli:
        raise PyinfraError("local.include is only available in CLI mode.")

    filename = get_file_path(state, filename)

    logger.debug("Including local file: %s", filename)

    config_state = config.get_current_state()

    try:
        # Fixes a circular import because `pyinfra.local` is really a CLI
        # only thing (so should be `pyinfra_cli.local`). It is kept here
        # to maintain backwards compatibility and the nicer public import
        # (ideally users never need to import from `pyinfra_cli`).

        from pyinfra_cli.util import exec_file

        with host.deploy(path.relpath(filename, state.cwd), None, None, in_deploy=False):
            exec_file(filename)

        # One potential solution to the above is to add local as an actual
        # module, ie `pyinfra.operations.local`.

    finally:
        config.set_current_state(config_state)


def shell(
    commands,
    splitlines: bool = False,
    ignore_errors: bool = False,
    print_output: bool = False,
    print_input: bool = False,
):
    """
    Subprocess based implementation of pyinfra/api/ssh.py's ``run_shell_command``.

    Args:
        commands (string, list): command or list of commands to execute
        splitlines (bool): optionally have the output split by lines
        ignore_errors (bool): ignore errors when executing these commands
    """

    if isinstance(commands, str):
        commands = [commands]

    all_stdout = []

    # Checking for state context being set means this function works outside a deploy
    # e.g.: the vagrant connector.
    if ctx_state.isset():
        print_output = state.print_output
        print_input = state.print_input

    for command in commands:
        print_prefix = "localhost: "

        if print_input:
            click.echo("{0}>>> {1}".format(print_prefix, command), err=True)

        return_code, combined_output = run_local_process(
            command,
            print_output=print_output,
            print_prefix=print_prefix,
        )
        stdout, stderr = split_combined_output(combined_output)

        if return_code > 0 and not ignore_errors:
            raise PyinfraError(
                "Local command failed: {0}\n{1}".format(command, stderr),
            )

        all_stdout.extend(stdout)

    if not splitlines:
        return "\n".join(all_stdout)

    return all_stdout
