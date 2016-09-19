# pyinfra
# File: pyinfra/local.py
# Desc: run stuff locally, within the context of operations - utility for the CLI

from __future__ import unicode_literals, print_function

from os import path
from subprocess import Popen, PIPE, STDOUT

import six

from . import pseudo_state
from .api.util import read_buffer, exec_file
from .api.exceptions import PyinfraError


def include(filename, hosts=None):
    '''
    Executes a local python file within the ``pyinfra.pseudo_state.deploy_dir`` directory.
    '''

    if not pseudo_state.active:
        return

    if hosts is not None:
        pseudo_state.limit_hosts = list(hosts)

    filename = path.join(pseudo_state.deploy_dir, filename)

    try:
        exec_file(filename)
    except IOError as e:
        raise PyinfraError(
            'Could not include local file: {0}\n{1}'.format(filename, e)
        )

    # Always clear any host limit
    finally:
        if isinstance(hosts, list):
            pseudo_state.limit_hosts = None


def shell(commands):
    '''
    Subprocess based implementation of pyinfra/api/ssh.py's ``run_shell_command``.
    '''

    if isinstance(commands, six.string_types):
        commands = [commands]

    all_stdout = []

    for command in commands:
        print_prefix = 'localhost: '

        if pseudo_state.print_output:
            print('{0}>>> {1}'.format(print_prefix, command))

        process = Popen(command, shell=True, stdout=PIPE, stderr=STDOUT)

        stdout = read_buffer(
            process.stdout,
            print_output=pseudo_state.print_output,
            print_func=lambda line: '{0}{1}'.format(print_prefix, line)
        )

        # Get & check result
        result = process.wait()

        # Close any open file descriptor
        process.stdout.close()

        if result > 0:
            raise PyinfraError(
                'Local command failed: {0}\n{1}'.format(command, stdout)
            )

        all_stdout.extend(stdout)

    return '\n'.join(all_stdout)
