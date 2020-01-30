from __future__ import print_function, unicode_literals

from os import path

import click
import six

import pyinfra

from . import logger, pseudo_host, pseudo_state
from .api.connectors.util import run_local_process, split_combined_output
from .api.exceptions import PyinfraError
from .api.util import ensure_host_list, get_caller_frameinfo


def include(filename, hosts=False, when=True):
    '''
    Executes a local python file within the ``pyinfra.pseudo_state.deploy_dir``
    directory.

    Args:
        hosts (string, list): group name or list of hosts to limit this include to
        when (bool): indicate whether to trigger operations in this include
    '''

    if not pyinfra.is_cli:
        raise PyinfraError('local.include is only available in CLI mode.')

    # TODO: remove this hosts/when
    if hosts is not False:
        logger.warning((
            'Use of the `hosts` argument is deprecated, '
            'please use normal `if` statements instead.'
        ))

    if when is not True:
        logger.warning((
            'Use of the `when` argument is deprecated, '
            'please use normal `if` statements instead.'
        ))

    if not when:
        return

    if hosts is not False:
        hosts = ensure_host_list(hosts, inventory=pseudo_state.inventory)
        if pseudo_host not in hosts:
            return
    # TODO: end remove hosts/when block

    if pseudo_state.deploy_dir:
        filename = path.join(pseudo_state.deploy_dir, filename)

    frameinfo = get_caller_frameinfo()

    logger.debug('Including local file: {0}'.format(filename))

    try:
        # Fixes a circular import because `pyinfra.local` is really a CLI
        # only thing (so should be `pyinfra_cli.local`). It is kept here
        # to maintain backwards compatibility and the nicer public import
        # (ideally users never need to import from `pyinfra_cli`).

        from pyinfra_cli.config import extract_file_config
        from pyinfra_cli.util import exec_file

        # Load any config defined in the file and setup like a @deploy
        config_data = extract_file_config(filename)
        kwargs = {
            key.lower(): value
            for key, value in six.iteritems(config_data)
            if key in [
                'SUDO', 'SUDO_USER', 'SU_USER',
                'PRESERVE_SUDO_ENV', 'IGNORE_ERRORS',
            ]
        }
        with pseudo_state.deploy(
            filename, kwargs, None, frameinfo.lineno,
            in_deploy=False,
        ):
            exec_file(filename)

        # One potential solution to the above is to add local as an actual
        # module, ie `pyinfra.modules.local`.

    except IOError as e:
        raise PyinfraError(
            'Could not include local file: {0}\n{1}'.format(filename, e),
        )


def shell(commands, splitlines=False, ignore_errors=False):
    '''
    Subprocess based implementation of pyinfra/api/ssh.py's ``run_shell_command``.

    Args:
        commands (string, list): command or list of commands to execute
        spltlines (bool): optionally have the output split by lines
        ignore_errors (bool): ignore errors when executing these commands
    '''

    if isinstance(commands, six.string_types):
        commands = [commands]

    all_stdout = []

    # Checking for pseudo_state means this function works outside a deploy
    # e.g.: the vagrant connector.
    print_output = pseudo_state.print_output if pseudo_state.isset() else False
    print_input = pseudo_state.print_input if pseudo_state.isset() else False

    for command in commands:
        print_prefix = 'localhost: '

        if print_input:
            click.echo('{0}>>> {1}'.format(print_prefix, command))

        return_code, combined_output = run_local_process(
            command,
            print_output=print_output,
            print_prefix=print_prefix,
        )
        stdout, stderr = split_combined_output(combined_output)

        if return_code > 0 and not ignore_errors:
            raise PyinfraError(
                'Local command failed: {0}\n{1}'.format(command, stderr),
            )

        all_stdout.extend(stdout)

    if not splitlines:
        return '\n'.join(all_stdout)

    return all_stdout
