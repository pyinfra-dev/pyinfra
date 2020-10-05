from __future__ import unicode_literals

from datetime import datetime


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

    string_to_format = (
        'sed -i.{backup_extension} "s/{0}/{1}/{2}" {3}'
        if interpolate_variables else
        "sed -i.{backup_extension} 's/{0}/{1}/{2}' {3}"
    )

    sed_command = string_to_format.format(
        line, replace, flags, filename,
        backup_extension=backup_extension,
    )

    if not backup:  # if we're not backing up, remove the file *if* sed succeeds
        sed_command = '{0} && rm -f {1}.{2}'.format(sed_command, filename, backup_extension)

    return sed_command


def chmod(target, mode, recursive=False):
    return 'chmod {0}{1} {2}'.format(('-R ' if recursive else ''), mode, target)


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

    return '{0}{1}{2} {3} {4}'.format(
        command,
        ' -R' if recursive else '',
        ' -h' if not dereference else '',
        user_group,
        target,
    )
