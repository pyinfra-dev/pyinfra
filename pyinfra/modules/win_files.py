'''
The win_files module handles windows filesystem state, file uploads and template generation.
'''

from __future__ import unicode_literals

import six

from pyinfra.api import operation, OperationError, OperationTypeError


@operation(pipeline_facts={
    'file': 'name',
})
def file(
    state, host, name,
    present=True, assume_present=False,
    user=None, group=None, mode=None, touch=False,
    create_remote_dir=False,
):
    '''
    Add/remove/update files.

    + name: name/path of the remote file
    + present: whether the file should exist
    + assume_present: whether to assume the file exists
    + user: user to own the files
    + group: group to own the files
    + mode: permissions of the files as an integer, eg: 755
    + touch: whether to touch the file
    + create_remote_dir: create the remote directory if it doesn't exist

    ``create_remote_dir``:
        If the remote directory does not exist it will be created using the same
        user & group as passed to ``files.put``. The mode will *not* be copied over,
        if this is required call ``files.directory`` separately.
    '''

    if not isinstance(name, six.string_types):
        raise OperationTypeError('Name must be a string')

    # mode = ensure_mode_int(mode)
    info = host.fact.file(name)

    # Not a file?!
    if info is False:
        raise OperationError('{0} exists and is not a file'.format(name))

#    # Doesn't exist & we want it
#    if not assume_present and info is None and present:
#        if create_remote_dir:
#            yield _create_remote_dir(state, host, name, user, group)
#
#        yield 'touch {0}'.format(name)
#
#        if mode:
#            yield chmod(name, mode)
#        if user or group:
#            yield chown(name, user, group)
#
#    # It exists and we don't want it
#    elif (assume_present or info) and not present:
#        yield 'rm -f {0}'.format(name)
#
#    # It exists & we want to ensure its state
#    elif (assume_present or info) and present:
#        if touch:
#            yield 'touch {0}'.format(name)
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
