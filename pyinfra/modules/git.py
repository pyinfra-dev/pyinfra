# pyinfra
# File: pyinfra/modules/git.py
# Desc: manage git repositories

from os import path

from pyinfra.api import operation


@operation
def repo(state, host, source, target, branch='master', pull=True, rebase=False):
    '''Manage git repositories.'''
    is_repo = host.directory(path.join(target, '.git'))
    commands = []

    # Cloning new repo?
    if not is_repo:
        commands.append('clone {0} --branch {1} .'.format(source, branch))

    # Ensuring existing repo
    else:
        current_branch = host.git_branch(target)
        if current_branch != branch:
            commands.append('checkout {0}'.format(branch))

        if pull:
            if rebase:
                commands.append('pull --rebase')
            else:
                commands.append('pull')

    # Attach prefixes for directory
    command_prefix = 'cd {0} && git'.format(target)
    commands = ['{0} {1}'.format(command_prefix, command) for command in commands]

    return commands
