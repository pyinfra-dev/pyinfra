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

    yield '''
        while ! (netstat -an | grep LISTEN | grep -e "\.{0}" -e ":{0}"); do
            echo "waiting for port {0}..."
            sleep 1
        done
    '''.format(port)


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

    for command in commands:
        if chdir:
            yield 'cd {0} && ({1})'.format(chdir, command)
        else:
            yield command


@operation
def script(state, host, filename, chdir=None):
    '''
    Upload and execute a local script on the remote host.

    + filename: local script filename to upload & execute
    + chdir: directory to cd into before executing the script
    '''

    temp_file = state.get_temp_filename(filename)
    yield files.put(state, host, filename, temp_file)

    yield chmod(temp_file, '+x')

    if chdir:
        yield 'cd {0} && {1}'.format(chdir, temp_file)
    else:
        yield temp_file


@operation
def group(
    state, host, name, present=True, system=False
):
    '''
    Manage system groups.

    + name: name of the group to ensure
    + present: whether the group should be present or not
    + system: whether to create a system group

    System users:
        System users don't exist on BSD, so the argument is ignored for BSD targets.
    '''

    groups = host.fact.groups or []
    is_present = name in groups

    # Group exists but we don't want them?
    if not present and is_present:
        yield 'groupdel {0}'.format(name)

    # Group doesn't exist and we want it?
    elif present and not is_present:
        args = []

        # BSD doesn't do system users
        if system and 'BSD' not in host.fact.os:
            args.append('-r')

        args.append(name)

        yield 'groupadd {0}'.format(' '.join(args))


@operation
def user(
    state, host, name,
    present=True, home=None, shell=None, group=None, groups=None,
    public_keys=None, delete_keys=False, ensure_home=True, system=False
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
    + delete_keys: whether to remove any keys not specified in ``public_keys``
    + ensure_home: whether to ensure the ``home`` directory exists
    + system: whether to create a system account

    Home directory:
        When ``ensure_home`` or ``public_keys`` are provided, ``home`` defaults to
        ``/home/{name}``.
    '''

    users = host.fact.users or {}
    user = users.get(name)

    if groups is None:
        groups = []

    if home is None:
        home = '/home/{0}'.format(name)

    # User not wanted?
    if not present:
        if user:
            yield 'userdel {0}'.format(name)
        return

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

        if system and host.fact.os not in ('OpenBSD', 'NetBSD'):
            args.append('-r')

        yield 'useradd {0} {1}'.format(' '.join(args), name)

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

        # Check secondary groups, if defined
        if groups and set(user['groups']) != set(groups):
            args.append('-G {0}'.format(','.join(groups)))

        # Need to mod the user?
        if args:
            yield 'usermod {0} {1}'.format(' '.join(args), name)

    # Ensure home directory ownership
    if ensure_home:
        yield files.directory(
            state, host, home,
            user=name, group=name,
        )

    # Add SSH keys
    if public_keys is not None:
        # Ensure .ssh directory
        # note that this always outputs commands unless the SSH user has access to the
        # authorized_keys file, ie the SSH user is the user defined in this function
        yield files.directory(
            state, host,
            '{0}/.ssh'.format(home),
            user=name, group=name,
            mode=700,
        )

        filename = '{0}/.ssh/authorized_keys'.format(home)

        if delete_keys:
            # Create a whole new authorized_keys file
            keys_file = six.StringIO('{0}\n'.format(
                '\n'.join(public_keys)
            ))

            # And ensure it exists
            yield files.put(
                state, host,
                keys_file, filename,
                user=name, group=name,
                mode=600,
            )

        else:
            # Ensure authorized_keys exists
            yield files.file(
                state, host, filename,
                user=name, group=name,
                mode=600,
            )

            # And every public key is present
            for key in public_keys:
                yield files.line(
                    state, host,
                    filename, key,
                )
