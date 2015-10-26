# pyinfra
# File: pyinfra/modules/local.py
# Desc: run stuff locally, within the context of operations

from subprocess import Popen, PIPE, STDOUT

from termcolor import colored

from pyinfra.api.util import read_buffer


print_local = False

def set_print_local(to_print):
    global print_local

    print_local = to_print


def shell(command, print_output=False):
    '''Subprocess based implementation of pyinfra/api/ssh.py's run_shell_command.'''

    print_prefix = '[{0}] '.format(colored('127.0.0.1', attrs=['bold']))

    if print_output or print_local:
        print '{0}>>> {1}'.format(print_prefix, command)

    process = Popen(command, shell=True, stdout=PIPE, stderr=STDOUT)

    stdout = read_buffer(
        process.stdout,
        print_output=print_output or print_local,
        print_func=lambda line: u'{0}{1}'.format(print_prefix, line)
    )

    return '\n'.join(stdout)
