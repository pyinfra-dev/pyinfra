# pyinfra
# File: pyinfra/modules/linux.py
# Desc: the base Linux module

from pyinfra.api import command, server, CommandError


@command
def user(name, present=True, home='/home/{0}', shell='/bin/bash', public_keys=None, delete_keys=False):
    commands = []
    is_present = name in server.fact('Users')

    def do_keys():
        pass

    # User exists but we don't want them?
    if is_present and not present:
        commands.append('userdel {0}'.format(name))

    # User doesn't exist but we want them?
    elif not is_present and present:
        # Create the user w/home/shell
        commands.append('adduser {0} --home {home} --shell {shell}'.format(
            name,
            home=home,
            shell=shell
        ))
        # Add SSH keys
        do_keys()

    # User exists and we want them, check home/shell/keys
    else:
        user = server.fact('Users')[name]
        # Check homedir
        if user['home'] != home:
            commands.append('usermod {0} --home {1}'.format(name, home))

        # Check shell
        if user['shell'] != home:
            commands.append('usermod {0} --shell {1}'.format(name, shell))

        # Add SSH keys
        do_keys()

    return commands


def _chmod(target, permissions, recursive=False):
    return 'chmod {0}{1} {2}'.format(('-R ' if recursive else ''), permissions, target)

def _chown(target, user, group, recursive=False):
    return 'chown {0}{1}:{2} {3}'.format(('-R ' if recursive else ''), user, group, target)

@command
def file(name, present=True, user=None, group=None, permissions=None):
    info = server.file(name)
    commands = []

    # It's a directory?!
    if info is False:
        raise CommandError('{0} is a directory'.format(name))

    # Doesn't exist & we want it
    if info is None and present:
        commands.append('touch {0}'.format(name))
        commands.append(_chmod(name, permissions))
        commands.append(_chown(name, user, group))

    # It exists and we don't want it
    elif not present:
        commands.append('rm -f {0}'.format(name))

    # It exists & we want to ensure its state
    else:
        # Check permissions
        if permissions and info['permissions'] != permissions:
            commands.append(_chmod(name, permissions))

        # Check user/group
        if user and group and (info['user'] != user or info['group'] != group):
            commands.append(_chown(name, user, group))

    return commands


@command
def directory(name, present=True, user=None, group=None, permissions=None, recursive=False):
    info = server.directory(name)
    commands = []

    # It's a file?!
    if info is False:
        raise CommandError('{0} is a file'.format(name))

    # Doesn't exist & we want it
    if info is None and present:
        commands.append('mkdir {0}'.format(name))
        commands.append(_chmod(name, permissions, recursive=recursive))
        commands.append(_chown(name, user, group, recursive=recursive))

    # It exists and we don't want it
    elif not present:
        commands.append('rm -rf {0}'.format(name))

    # It exists & we want to ensure its state
    else:
        # Check permissions
        if permissions and info['permissions'] != permissions:
            commands.append(_chmod(name, permissions, recursive=recursive))

        # Check user/group
        if user and group and (info['user'] != user or info['group'] != group):
            commands.append(_chown(name, user, group, recursive=recursive))

    return commands


@command
def service(name, running=True, restarted=False):
    if running:
        return 'service {0} status || service {0} start'.format(name)
    else:
        return 'service {0} stop'.format(name)

    if restarted:
        return 'service {0} restart'.format(name)
