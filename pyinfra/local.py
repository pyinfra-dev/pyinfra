from os import path
from subprocess import PIPE, Popen, STDOUT

from gevent.queue import Queue

import pyinfra

from . import logger, pseudo_host, pseudo_state
from .api.exceptions import PyinfraError
from .api.util import ensure_host_list, get_caller_frameinfo, read_buffer


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

    if not when:
        return

    if hosts is not False:
        hosts = ensure_host_list(hosts, inventory=pseudo_state.inventory)
        if pseudo_host not in hosts:
            return

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
            for key, value in config_data.items()
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

    if isinstance(commands, str):
        commands = [commands]

    all_stdout = []

    # Checking for pseudo_state means this function works outside a deploy
    # e.g.: the vagrant connector.
    print_output = (
        pseudo_state.print_output
        if pseudo_state.isset()
        else False
    )

    for command in commands:
        print_prefix = 'localhost: '

        if print_output:
            print('{0}>>> {1}'.format(print_prefix, command))

        process = Popen(command, shell=True, stdout=PIPE, stderr=STDOUT)

        stdout_queue = Queue()

        read_buffer(
            'stdout',
            process.stdout,
            stdout_queue,
            print_output=print_output,
            print_func=lambda line: '{0}{1}'.format(print_prefix, line),
        )

        stdout = [line for _, line in stdout_queue.queue]

        # Get & check result
        result = process.wait()

        # Close any open file descriptor
        process.stdout.close()

        if result > 0 and not ignore_errors:
            raise PyinfraError(
                'Local command failed: {0}\n{1}'.format(command, stdout),
            )

        all_stdout.extend(stdout)

    if not splitlines:
        return '\n'.join(all_stdout)

    return all_stdout
