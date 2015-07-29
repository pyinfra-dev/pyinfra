# pyinfra
# File: pyinfra/modules/git.py
# Desc: manage git repositories

from os import path

from pyinfra import host
from pyinfra.api import operation


@operation
def repo(source, target, branch='master', pull=True, rebase=False):
    '''Manage git repositories.'''
    is_repo = host.directory(path.join(target, '.git'))
    command_prefix = 'cd {0} && git'.format(target)
    commands = []

    if not is_repo:
        commands.append('{0} clone {1} .'.format(command_prefix, source))

    else:
        if pull:
            if rebase:
                commands.append('{0} pull --rebase'.format(command_prefix))
            else:
                commands.append('{0} pull'.format(command_prefix))

    return commands
