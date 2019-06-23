# pyinfra
# File: pyinfra/modules/server.py
# Desc: the base os-level module

'''
The server module takes care of os-level state. Targets POSIX compatibility, tested on
Linux/BSD.
'''

from __future__ import unicode_literals

import six
from six.moves import shlex_quote

from pyinfra.api import operation

from . import files
from .util.files import chmod, sed_replace


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
def script_template(state, host, template_filename, chdir=None, **data):
    '''
    Generate, upload and execute a local script template on the remote host.

    + template_filename: local script template filename
    + chdir: directory to cd into before executing the script
    '''

    temp_file = state.get_temp_filename(template_filename)
    yield files.template(state, host, template_filename, temp_file, **data)

    yield chmod(temp_file, '+x')

    if chdir:
        yield 'cd {0} && {1}'.format(chdir, temp_file)
    else:
        yield temp_file


@operation
def modprobe(state, host, name, present=True, force=False):
    '''
    Load/unload kernel modules.

    + name: name of the module to manage
    + present: whether the module should be loaded or not
    + force: whether to force any add/remove modules
    '''

    modules = host.fact.kernel_modules
    is_present = name in modules

    args = ''
    if force:
        args = ' -f'

    # Module is loaded and we don't want it?
    if not present and is_present:
        yield 'modprobe{0} -r {1}'.format(args, name)

    # Module isn't loaded and we want it?
    elif present and not is_present:
        yield 'modprobe{0} {1}'.format(args, name)


@operation
def hostname(state, host, hostname, hostname_file=None):
    '''
    Set the system hostname.

    + hostname: the hostname that should be set
    + hostname_file: the file that permanently sets the hostname

    Hostname file:
        By default pyinfra will auto detect this by targetting ``/etc/hostname``
        on Linux and ``/etc/myname`` on OpenBSD.
    '''

    if hostname_file is None:
        os = host.fact.os

        if os == 'Linux':
            hostname_file = '/etc/hostname'
        elif os == 'OpenBSD':
            hostname_file = '/etc/myname'

    current_hostname = host.fact.hostname

    if current_hostname != hostname:
        yield 'hostname {0}'.format(hostname)

    if hostname_file:
        # Create a whole new hostname file
        file = six.StringIO('{0}\n'.format(hostname))

        # And ensure it exists
        yield files.put(
            state, host,
            file, hostname_file,
        )


@operation
def sysctl(
    state, host, name, value,
    persist=False, persist_file='/etc/sysctl.conf',
):
    '''
    Edit sysctl configuration.

    + name: name of the sysctl setting to ensure
    + value: the value or list of values the sysctl should be
    + persist: whether to write this sysctl to the config
    + persist_file: file to write the sysctl to persist on reboot
    '''

    string_value = (
        ' '.join(value)
        if isinstance(value, list)
        else value
    )

    existing_value = host.fact.sysctl.get(name)
    if not existing_value or existing_value != value:
        yield 'sysctl {0}={1}'.format(name, string_value)

    if persist:
        yield files.line(
            state, host,
            persist_file,
            '{0}[[:space:]]*=[[:space:]]*{1}'.format(name, string_value),
            replace='{0} = {1}'.format(name, string_value),
        )


@operation
def crontab(
    state, host, command, present=True, user=None, name=None,
    minute='*', hour='*', month='*', day_of_week='*', day_of_month='*',
):
    '''
    Add/remove/update crontab entries.

    + command: the command for the cron
    + present: whether this cron command should exist
    + user: the user whose crontab to manage
    + name: name the cronjob so future changes to the command will overwrite
    + minute: which minutes to execute the cron
    + hour: which hours to execute the cron
    + month: which months to execute the cron
    + day_of_week: which day of the week to execute the cron
    + day_of_month: which day of the month to execute the cron

    Cron commands:
        Unless ``name`` is specified the command is used to identify crontab entries.
        This means commands must be unique within a given users crontab. If you require
        multiple identical commands, provide a different name argument for each.
    '''

    crontab = host.fact.crontab(user)
    name_comment = '# pyinfra-name={0}'.format(name)

    existing_crontab = crontab.get(command)
    existing_crontab_match = command

    if not existing_crontab and name:  # find the crontab by name if provided
        for cmd, details in crontab.items():
            if name_comment in details['comments']:
                existing_crontab = details
                existing_crontab_match = cmd

    exists = existing_crontab is not None

    edit_commands = []
    temp_filename = state.get_temp_filename()

    new_crontab_line = '{minute} {hour} {day_of_month} {month} {day_of_week} {command}'.format(
        command=command,
        minute=minute,
        hour=hour,
        month=month,
        day_of_week=day_of_week,
        day_of_month=day_of_month,
    )
    existing_crontab_match = '.*{0}.*'.format(existing_crontab_match)

    # Don't want the cron and it does exist? Remove the line
    if not present and exists:
        edit_commands.append(sed_replace(
            temp_filename, existing_crontab_match, '',
        ))

    # Want the cron but it doesn't exist? Append the line
    elif present and not exists:
        if name:
            edit_commands.append('echo {0} >> {1}'.format(
                shlex_quote(name_comment), temp_filename,
            ))

        edit_commands.append('echo {0} >> {1}'.format(
            shlex_quote(new_crontab_line), temp_filename,
        ))

    # We have the cron and it exists, do it's details? If not, replace the line
    elif present and exists:
        if any((
            minute != existing_crontab['minute'],
            hour != existing_crontab['hour'],
            month != existing_crontab['month'],
            day_of_week != existing_crontab['day_of_week'],
            day_of_month != existing_crontab['day_of_month'],
        )):
            edit_commands.append(sed_replace(
                temp_filename, existing_crontab_match, new_crontab_line,
            ))

    if edit_commands:
        crontab_args = []
        if user:
            crontab_args.append('-u {0}'.format(user))

        # List the crontab into a temporary file if it exists
        if crontab:
            yield 'crontab -l {0} > {1}'.format(' '.join(crontab_args), temp_filename)

        # Now yield any edits
        for edit_command in edit_commands:
            yield edit_command

        # Finally, use the tempfile to write a new crontab
        yield 'crontab {0} {1}'.format(' '.join(crontab_args), temp_filename)


@operation
def group(
    state, host, name, present=True, system=False, gid=None,
):
    '''
    Add/remove system groups.

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

        if gid:
            args.append('--gid {0}'.format(gid))

        yield 'groupadd {0}'.format(' '.join(args))


@operation
def user(
    state, host, name,
    present=True, home=None, shell=None, group=None, groups=None,
    public_keys=None, delete_keys=False, ensure_home=True,
    system=False, uid=None,
):
    '''
    Add/remove/update system users & their ssh `authorized_keys`.

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

        if system and 'BSD' not in host.fact.os:
            args.append('-r')

        if uid:
            args.append('--uid {0}'.format(uid))

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
                '\n'.join(public_keys),
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
