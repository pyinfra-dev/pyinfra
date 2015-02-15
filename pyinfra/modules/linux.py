# pyinfra
# File: pyinfra/modules/linux.py
# Desc: the base Linux module

from pyinfra.api import operation, server, CommandError


@operation
def user(name, present=True, home='/home/{0}', shell='/bin/bash', public_keys=None, delete_keys=False):
    commands = []
    is_present = name in server.fact('Users')

    def do_keys():
        if delete_keys:
            commands.append('rm -f {0}/.ssh/authorized_keys*'.format(home))

        if not public_keys: return

        # Ensure .ssh directory & authorized_keys file
        commands.extend(
            directory.inline(name='{}/.ssh'.format(home), present=True)
        )
        commands.extend(
            file.inline(name='{0}/.ssh/authorized_keys'.format(home), present=True)
        )

        for key in public_keys:
            commands.append('cat {1}/.ssh/authorized_keys | grep "{0}" || echo "{0}" >> {1}/.ssh/authorized_keys'.format(key, home))

    # User exists but we don't want them?
    if is_present and not present:
        commands.append('userdel {0}'.format(name))

    # User doesn't exist but we want them?
    elif not is_present and present:
        # Create the user w/home/shell
        commands.append('useradd {0} --home {home} --shell {shell}'.format(
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
            commands.append('usermod --home {1} {0}'.format(name, home))

        # Check shell
        if user['shell'] != shell:
            commands.append('usermod --shell {1} {0}'.format(name, shell))

        # Add SSH keys
        do_keys()

    return commands


def _chmod(target, permissions, recursive=False):
    return 'chmod {0}{1} {2}'.format(('-R ' if recursive else ''), permissions, target)

def _chown(target, user, group, recursive=False):
    return 'chown {0}{1}:{2} {3}'.format(('-R ' if recursive else ''), user, group, target)

@operation
def file(name, present=True, user=None, group=None, permissions=None, touch=False):
    info = server.file(name)
    commands = []

    # It's a directory?!
    if info is False:
        raise CommandError('{} is a directory'.format(name))

    # Doesn't exist & we want it
    if info is None and present:
        commands.append('touch {}'.format(name))
        if permissions:
            commands.append(_chmod(name, permissions))
        if user or group:
            commands.append(_chown(name, user, group))

    # It exists and we don't want it
    elif not present:
        commands.append('rm -f {}'.format(name))

    # It exists & we want to ensure its state
    else:
        if touch:
            commands.append('touch {}'.format(name))

        # Check permissions
        if permissions and info['permissions'] != permissions:
            commands.append(_chmod(name, permissions))

        # Check user/group
        if user and group and (info['user'] != user or info['group'] != group):
            commands.append(_chown(name, user, group))

    return commands


@operation
def directory(name, present=True, user=None, group=None, permissions=None, recursive=False):
    info = server.directory(name)
    commands = []

    # It's a file?!
    if info is False:
        raise CommandError('{} is a file'.format(name))

    # Doesn't exist & we want it
    if info is None and present:
        commands.append('mkdir -p {}'.format(name))
        if permissions:
            commands.append(_chmod(name, permissions, recursive=recursive))
        if user or group:
            commands.append(_chown(name, user, group, recursive=recursive))

    # It exists and we don't want it
    elif not present:
        commands.append('rm -rf {}'.format(name))

    # It exists & we want to ensure its state
    else:
        # Check permissions
        if permissions and info['permissions'] != permissions:
            commands.append(_chmod(name, permissions, recursive=recursive))

        # Check user/group
        if user and group and (info['user'] != user or info['group'] != group):
            commands.append(_chown(name, user, group, recursive=recursive))

    return commands


@operation
def init(name, running=True, restarted=False):
    if running:
        return ['/etc/init.d/{0} status || /etc/init.d/{0} start'.format(name)]
    else:
        return ['/etc/init.d/{} stop'.format(name)]

    if restarted:
        return ['/etc/init.d/{} restart'.format(name)]
