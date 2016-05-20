# pyinfra
# File: pyinfra/modules/server.py
# Desc: the base os-level module

'''
The server module takes care of os-level state. Targets POSIX compatability, tested on
Linux/BSD.
'''

from __future__ import unicode_literals

import six

from pyinfra.api import operation

from . import files
from .util.files import chmod


@operation
def wait(state, host, port=None):
    '''
    Waits for a port to come active on the target machine. Requires netstat, checks every
    1s.

    + port: port number to wait for
    '''

    return ['''
        while ! (netstat -an | grep LISTEN | grep -e "\.{0}" -e ":{0}"); do
            echo "waiting for port {0}..."
            sleep 1
        done
    '''.format(port)]


@operation
def shell(state, host, commands, chdir=None):
    '''
    Run raw shell code.

    + commands: command or list of commands to execute on the remote server
    + chdir: directory to cd into before executing commands
    '''

    # Ensure we have a list
    if isinstance(commands, six.string_types):
        commands = [commands]

    if chdir:
        commands = [
            'cd {0} && ({1})'.format(chdir, command)
            for command in commands
        ]

    return commands


@operation
def script(state, host, filename, chdir=None):
    '''
    Upload and execute a local script on the remote host.

    + filename: local script filename to upload & execute
    + chdir: directory to cd into before executing the script
    '''

    commands = []

    temp_file = state.get_temp_filename(filename)
    commands.extend(files.put(state, host, filename, temp_file))

    commands.append(chmod(temp_file, '+x'))

    if chdir:
        commands.append('cd {0} && {1}'.format(chdir, temp_file))
    else:
        commands.append(temp_file)

    return commands


@operation
def group(
    state, host, name, present=True
):
    '''
    Manage system groups.

    + name: name of the group to ensure
    + present: whether the group should be present or not
    '''

    commands = []
    groups = host.fact.groups or []
    is_present = name in groups

    # Group exists but we don't want them?
    if not present and is_present:
        commands.append('groupdel {0}'.format(name))

    # Group doesn't exist and we want it?
    elif present and not is_present:
        commands.append('groupadd {0}'.format(name))

    return commands


@operation
def user(
    state, host, name,
    present=True, home=None, shell=None, group=None, groups=None,
    public_keys=None, ensure_home=True
):
    '''
    Manage system users & their ssh `authorized_keys`. Options:

    + name: name of the user to ensure
    + present: whether this user should exist
    + home: the users home directory
    + shell: the users shell
    + group: the users primary group
    + groups: the users secondary groups
    + public_keys: list of public keys to attach to this user, ``home`` must be specified
    + ensure_home: whether to ensure the ``home`` directory exists
    '''

    commands = []
    users = host.fact.users or {}
    user = users.get(name)

    if groups is None:
        groups = []

    # User exists but we don't want them?
    if not present and user:
        commands.append('userdel {0}'.format(name))
        return commands

    # User doesn't exist but we want them?
    if present and user is None:
        # Create the user w/home/shell
        args = []

        if home:
            args.append('-d {0}'.format(home))

        if shell:
            args.append('-s {0}'.format(shell))

        if group:
            args.append('-g {0}'.format(group))

        if groups:
            args.append('-G {0}'.format(','.join(groups)))

        commands.append('useradd {0} {1}'.format(' '.join(args), name))

    # User exists and we want them, check home/shell/keys
    else:
        args = []

        # Check homedir
        if home and user['home'] != home:
            args.append('-d {0}'.format(home))

        # Check shell
        if shell and user['shell'] != shell:
            args.append('-s {0}'.format(shell))

        # Check primary group
        if group and user['group'] != group:
            args.append('-g {0}'.format(group))

        # Check secondary groups
        if set(user['groups']) != set(groups):
            args.append('-G {0}'.format(','.join(groups)))

        # Need to mod the user?
        if args:
            commands.append('usermod {0} {1}'.format(' '.join(args), name))

    # Ensure home directory ownership
    if home:
        if ensure_home:
            commands.extend(files.directory(
                state, host, home,
                user=name, group=name
            ))

        # Add SSH keys
        if public_keys is not None:
            # Ensure .ssh directory
            # note that this always outputs commands unless the SSH user has access to the
            # authorized_keys file, ie the SSH user is the user defined in this function
            commands.extend(files.directory(
                state, host,
                '{0}/.ssh'.format(home),
                user=name, group=name,
                mode=700
            ))

            filename = '{0}/.ssh/authorized_keys'.format(home)

            # Ensure authorized_keys
            commands.extend(files.file(
                state, host, filename,
                user=name, group=name,
                mode=600
            ))

            for key in public_keys:
                commands.extend(files.line(
                    state, host,
                    filename, key
                ))

    return commands
