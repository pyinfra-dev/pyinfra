from __future__ import unicode_literals

from datetime import datetime

from pyinfra.api import QuoteString, StringCommand


def ensure_mode_int(mode):
    # Already an int (/None)?
    if isinstance(mode, int) or mode is None:
        return mode

    try:
        # Try making an int ('700' -> 700)
        return int(mode)

    except (TypeError, ValueError):
        pass

    # Return as-is (ie +x which we don't need to normalise, it always gets run)
    return mode


def ensure_whole_line_match(line):
    # Ensure we're matching a whole ^line$
    if not line.startswith('^'):
        line = '^.*{0}'.format(line)

    if not line.endswith('$'):
        line = '{0}.*$'.format(line)

    return line


def get_timestamp():
    return datetime.now().strftime('%y%m%d%H%M')


def sed_replace(
    filename,
    line,
    replace,
    flags=None,
    backup=False,
    interpolate_variables=False,
):
    flags = ''.join(flags) if flags else ''

    line = line.replace('/', r'\/')
    replace = str(replace)
    replace = replace.replace('/', r'\/')
    backup_extension = get_timestamp()

    if interpolate_variables:
        line = line.replace('"', '\\"')
        replace = replace.replace('"', '\\"')
        sed_script_formatter = '"s/{0}/{1}/{2}"'
    else:
        # Single quotes cannot contain other single quotes, even when escaped , so turn
        # each ' into '"'"' (end string, double quote the single quote, (re)start string)
        line = line.replace("'", "'\"'\"'")
        replace = replace.replace("'", "'\"'\"'")
        sed_script_formatter = "'s/{0}/{1}/{2}'"

    sed_script = sed_script_formatter.format(line, replace, flags)

    sed_command = StringCommand(
        'sed', '-i.{0}'.format(backup_extension), sed_script, QuoteString(filename),
    )

    if not backup:  # if we're not backing up, remove the file *if* sed succeeds
        backup_filename = '{0}.{1}'.format(filename, backup_extension)
        sed_command = StringCommand(sed_command, '&&', 'rm', '-f', QuoteString(backup_filename))

    return sed_command


def chmod(target, mode, recursive=False):
    args = ['chmod']
    if recursive:
        args.append('-R')

    args.append('{0}'.format(mode))

    return StringCommand(' '.join(args), QuoteString(target))


def chown(target, user, group=None, recursive=False, dereference=True):
    command = 'chown'
    user_group = None

    if user and group:
        user_group = '{0}:{1}'.format(user, group)

    elif user:
        user_group = user

    elif group:
        command = 'chgrp'
        user_group = group

    args = [command]
    if recursive:
        args.append('-R')

    if not dereference:
        args.append('-h')

    return StringCommand(' '.join(args), user_group, QuoteString(target))
