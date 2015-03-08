# pyinfra
# File: pyinfra/modules/linux.py
# Desc: the base Linux module

from pyinfra import host
from pyinfra.api import operation, CommandError


@operation
def shell(code):
    '''[Not implemented] Run raw shell code.'''
    return [code]


@operation
def script(code=None, file=None):
    '''[Not implemented] Run a script or file.'''
    if code is not None:
        return code

    if file is not None:
        return 'whaaa'


@operation
def init(name, running=True, restarted=False):
    '''Manage the state of init.d services.'''
    if running:
        return ['/etc/init.d/{0} status || /etc/init.d/{0} start'.format(name)]
    else:
        return ['/etc/init.d/{} stop'.format(name)]

    if restarted:
        return ['/etc/init.d/{} restart'.format(name)]


@operation
def user(name, present=True, home=None, shell=None, public_keys=None, delete_keys=False):
    '''
    Manage Linux users & their ssh `authorized_keys`.

    # public_keys: list of public keys to attach to this user
    # delete_keys: deletes existing keys when `public_keys` specified
    '''
    commands = []
    is_present = name in host.users

    def do_keys():
        if public_keys is None:
            return

        # Ensure .ssh directory
        commands.extend(directory.__decorated__(
            name='{}/.ssh'.format(home), present=True
        ))

        filename = '{}/.ssh/authorized_keys'.format(home)
        if delete_keys:
            commands.extend([
                # Delete all authorized_keys files
                'rm -f {}*'.format(filename),
                # Re-create just the one
                'touch {}'.format(filename)
            ])

        for key in public_keys:
            commands.append('cat {0} | grep "{1}" || echo "{1}" >> {0}'.format(filename, key))

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
        user = host.users[name]
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
    '''Manage the state of files.'''
    info = host.file(name)
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
    '''Manage the state of directories.'''
    info = host.directory(name)
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
