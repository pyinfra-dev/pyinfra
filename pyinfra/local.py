# pyinfra
# File: pyinfra/local.py
# Desc: run stuff locally, within the context of operations - utility for the CLI

from os import path
from subprocess import Popen, PIPE, STDOUT

from . import pseudo_state
from .api.util import read_buffer


print_local = False

def set_print_local(to_print):
    global print_local

    print_local = to_print


def include(filename):
    '''
    Execute a local python file within the ``pyinfra.pseudo_state.deploy_dir`` directory.
    '''
    filename = path.join(pseudo_state.deploy_dir, filename)
    execfile(filename)


def shell(command, print_output=False):
    '''Subprocess based implementation of pyinfra/api/ssh.py's run_shell_command.'''

    print_prefix = 'localhost: '

    if print_output or print_local:
        print '{0}>>> {1}'.format(print_prefix, command)

    process = Popen(command, shell=True, stdout=PIPE, stderr=STDOUT)

    stdout = read_buffer(
        process.stdout,
        print_output=print_output or print_local,
        print_func=lambda line: u'{0}{1}'.format(print_prefix, line)
    )

    return '\n'.join(stdout)
