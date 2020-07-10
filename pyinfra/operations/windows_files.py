'''
The windows_files module handles windows filesystem state, file uploads and template generation.
'''

from __future__ import unicode_literals

import ntpath

import six

from pyinfra import logger
from pyinfra.api import operation, OperationError, OperationTypeError


@operation(pipeline_facts={
    'windows_file': 'name',
})
def file(
    name,
    present=True, assume_present=False,
    user=None, group=None, mode=None, touch=False,
    create_remote_dir=True,
    state=None, host=None,
):
    '''
    Add/remove/update files.

    + name: name/path of the remote file
    + present: whether the file should exist
    + assume_present: whether to assume the file exists
    + TODO: user: user to own the files
    + TODO: group: group to own the files
    + TODO: mode: permissions of the files as an integer, eg: 755
    + touch: whether to touch the file
    + create_remote_dir: create the remote directory if it doesn't exist

    ``create_remote_dir``:
        If the remote directory does not exist it will be created using the same
        user & group as passed to ``files.put``. The mode will *not* be copied over,
        if this is required call ``files.directory`` separately.

    Example:

    .. code:: python

        files.file(
            name='Create c:\\temp\\hello.txt',
            path='c:\\temp\\hello.txt',
            touch=True,
        )
    '''

    if not isinstance(name, six.string_types):
        raise OperationTypeError('Name must be a string')

    # mode = ensure_mode_int(mode)
    info = host.fact.windows_file(name)

    # Not a file?!
    if info is False:
        raise OperationError('{0} exists and is not a file'.format(name))

    # Doesn't exist & we want it
    if not assume_present and info is None and present:
        if create_remote_dir:
            yield _create_remote_dir(state, host, name, user, group)

        yield 'New-Item -ItemType file {0}'.format(name)

#        if mode:
#            yield chmod(name, mode)
#        if user or group:
#            yield chown(name, user, group)

    # It exists and we don't want it
    elif (assume_present or info) and not present:
        yield 'Remove-Item {0}'.format(name)

#    # It exists & we want to ensure its state
#    elif (assume_present or info) and present:
#        if touch:
#            yield 'New-Item -ItemType file {0}'.format(name)
#
#        # Check mode
#        if mode and (not info or info['mode'] != mode):
#            yield chmod(name, mode)
#
#        # Check user/group
#        if (
#            (not info and (user or group))
#            or (user and info['user'] != user)
#            or (group and info['group'] != group)
#        ):
#            yield chown(name, user, group)


def windows_file(*args, **kwargs):
    # COMPAT
    # TODO: remove this
    logger.warning((
        'Use of `windows_files.windows_file` is deprecated, '
        'please use `windows_files.file` instead.'
    ))
    return file(*args, **kwargs)


def _create_remote_dir(state, host, remote_filename, user, group):
    # Always use POSIX style path as local might be Windows, remote always *nix
    remote_dirname = ntpath.dirname(remote_filename)
    if remote_dirname:
        yield directory(
            state, host, remote_dirname,
            user=user, group=group,
        )


@operation(pipeline_facts={
    'windows_directory': 'name',
})
def directory(
    name,
    present=True, assume_present=False,
    user=None, group=None, mode=None, recursive=False,
    state=None, host=None,
):
    '''
    Add/remove/update directories.

    + name: name/path of the remote folder
    + present: whether the folder should exist
    + assume_present: whether to assume the directory exists
    + TODO: user: user to own the folder
    + TODO: group: group to own the folder
    + TODO: mode: permissions of the folder
    + TODO: recursive: recursively apply user/group/mode

    Examples:

    .. code:: python

        files.directory(
            name='Ensure the c:\\temp\\dir_that_we_want_removed is removed',
            path='c:\\temp\\dir_that_we_want_removed',
            present=False,
        )

        files.directory(
            name='Ensure c:\\temp\\foo\\foo_dir exists',
            path='c:\\temp\\foo\\foo_dir',
            recursive=True,
        )

        # multiple directories
        dirs = ['c:\\temp\\foo_dir1', 'c:\\temp\\foo_dir2']
        for dir in dirs:
            files.directory(
                name='Ensure the directory `{}` exists'.format(dir),
                path=dir,
            )

    '''

    if not isinstance(name, six.string_types):
        raise OperationTypeError('Name must be a string')

    info = host.fact.windows_directory(name)

    # Not a directory?!
    if info is False:
        raise OperationError('{0} exists and is not a directory'.format(name))

    # Doesn't exist & we want it
    if not assume_present and info is None and present:
        yield 'mkdir -p {0}'.format(name)
#        if mode:
#            yield chmod(name, mode, recursive=recursive)
#        if user or group:
#            yield chown(name, user, group, recursive=recursive)
#
    # It exists and we don't want it
    elif (assume_present or info) and not present:
        # TODO: how to ensure we use 'ps'?
        # remove anything in the directory
        yield 'Get-ChildItem {0} -Recurse | Remove-Item'.format(name)
        # remove directory
        yield 'Remove-Item {0}'.format(name)

    # It exists & we want to ensure its state
#    elif (assume_present or info) and present:
#        # Check mode
#        if mode and (not info or info['mode'] != mode):
#            yield chmod(name, mode, recursive=recursive)
#
#        # Check user/group
#        if (
#            (not info and (user or group))
#            or (user and info['user'] != user)
#            or (group and info['group'] != group)
#        ):
#            yield chown(name, user, group, recursive=recursive)


def windows_directory(*args, **kwargs):
    # COMPAT
    # TODO: remove this
    logger.warning((
        'Use of `windows_files.windows_directory` is deprecated, '
        'please use `windows_files.directory` instead.'
    ))
    return directory(*args, **kwargs)
