# pyinfra
# File: pyinfra/modules/util/files.py
# Desc: common functions for handling the filesystem


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
