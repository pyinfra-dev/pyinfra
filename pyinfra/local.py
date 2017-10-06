# pyinfra
# File: pyinfra/local.py
# Desc: run stuff locally, within the context of operations - utility for the CLI

from __future__ import print_function, unicode_literals

from os import path
from subprocess import PIPE, Popen, STDOUT

import six

from . import logger, pseudo_inventory, pseudo_state
from .api.exceptions import PyinfraError
from .api.util import ensure_host_list, exec_file, read_buffer


def include(filename, hosts=False):
    '''
    Executes a local python file within the ``pyinfra.pseudo_state.deploy_dir``
    directory.
    '''

    filename = path.join(pseudo_state.deploy_dir, filename)

    logger.debug('Including local file: {0}'.format(filename))

    try:
        if hosts is not False:
            hosts = ensure_host_list(hosts, pseudo_inventory)
            with pseudo_state.limit(hosts):
                exec_file(filename)

        else:
            exec_file(filename)

    except IOError as e:
        raise PyinfraError(
            'Could not include local file: {0}\n{1}'.format(filename, e),
        )


def shell(commands, splitlines=False, ignore_errors=False):
    '''
    Subprocess based implementation of pyinfra/api/ssh.py's ``run_shell_command``.
    '''

    if isinstance(commands, six.string_types):
        commands = [commands]

    all_stdout = []

    # Checking for pseudo_state means this function works outside a deploy
    # eg the vagrant connector.
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

        stdout = read_buffer(
            process.stdout,
            print_output=print_output,
            print_func=lambda line: '{0}{1}'.format(print_prefix, line),
        )

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
