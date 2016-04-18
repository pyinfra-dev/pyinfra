# pyinfra
# File: pyinfra/modules/util/files.py
# Desc: common functions for handling the filesystem

from __future__ import unicode_literals


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


def sed_replace(state, filename, line, replace, flags=None):
    flags = ''.join(flags) if flags else ''

    line = line.replace('/', '\/')
    replace = replace.replace('/', '\/')

    return 'sed -i "s/{0}/{1}/{2}" {3}'.format(
        line, replace, flags, filename
    )


def chmod(target, mode, recursive=False):
    return 'chmod {0}{1} {2}'.format(('-R ' if recursive else ''), mode, target)


def chown(target, user, group=None, recursive=False):
    command = 'chown'
    user_group = None

    if user and group:
        user_group = '{0}:{1}'.format(user, group)

    elif user:
        user_group = user

    elif group:
        command = 'chgrp'
        user_group = group

    return '{0}{1} {2} {3}'.format(
        command,
        ' -R' if recursive else '',
        user_group,
        target
    )
