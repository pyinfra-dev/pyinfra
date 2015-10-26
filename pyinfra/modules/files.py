# pyinfra
# File: pyinfra/modules/files.py
# Desc: manage files/templates <> server

'''
The files module handles filesystem state, file uploads and template generation.
'''

from os import path, walk
from cStringIO import StringIO

from jinja2 import Template

from pyinfra.api import operation, OperationException
from pyinfra.api.util import get_file_sha1


def _chmod(target, mode, recursive=False):
    return 'chmod {0}{1} {2}'.format(('-R ' if recursive else ''), mode, target)

def _chown(target, user, group, recursive=False):
    if user and group:
        user_group = '{0}:{1}'.format(user, group)
    else:
        user_group = user or group

    return 'chown {0}{1} {2}'.format(('-R ' if recursive else ''), user_group, target)


@operation
def sync(state, host, source, destination, user=None, group=None, mode=None, delete=False):
    '''
    Syncs a local directory with a remote one, with delete support. Note that delete will
    remove extra files on the remote side, but not extra directories.
    '''
    # If we don't enforce the source ending with /, remote_dirname below might start with
    # a /, which makes the path.join cut off the destination bit.
    if not source.endswith(path.sep):
        source = '{0}{1}'.format(source, path.sep)

    # Source relative to deploy.py
    source_dir = path.join(state.deploy_dir, source)

    put_files = []
    ensure_dirnames = []
    for dirname, _, filenames in walk(source_dir):
        remote_dirname = dirname.replace(source_dir, '')

        if remote_dirname:
            ensure_dirnames.append(remote_dirname)

        for filename in filenames:
            put_files.append((
                path.join(dirname, filename),
                path.join(destination, remote_dirname, filename)
            ))

    commands = []

    # Ensure the destination directory
    commands.extend(directory(destination, user=user, group=group, mode=mode))

    # Ensure any remote dirnames
    for dirname in ensure_dirnames:
        commands.extend(directory(
            '{0}/{1}'.format(destination, dirname),
            user=user, group=group, mode=mode
        ))

    # Put each file combination
    for local_filename, remote_filename in put_files:
        commands.extend(put(
            local_filename, remote_filename,
            user=user, group=group, mode=mode,
            add_deploy_dir=False
        ))

    # Delete any extra files
    if delete:
        remote_filenames = set(host.find_files(destination) or [])
        wanted_filenames = set([remote_filename for _, remote_filename in put_files])
        files_to_delete = remote_filenames - wanted_filenames
        for filename in files_to_delete:
            commands.extend(file(filename, present=False))

    return commands


@operation
def put(
    state, host, local_filename, remote_filename,
    user=None, group=None, mode=None, add_deploy_dir=True
):
    '''Copy a local file to the remote system.'''
    if state.deploy_dir and add_deploy_dir:
        local_filename = path.join(state.deploy_dir, local_filename)

    local_file = open(local_filename, 'r')
    remote_file = host.file(remote_filename)
    commands = []

    # No remote file, always upload and user/group/mode if supplied
    if not remote_file:
        commands.append((local_file, remote_filename))

        if user or group:
            commands.append(_chown(remote_filename, user, group))

        if mode:
            commands.append(_chmod(remote_filename, mode))

    # File exists, check sum and check user/group/mode if supplied
    else:
        local_sum = get_file_sha1(local_file)
        remote_sum = host.sha1_file(remote_filename)

        # Check sha1sum, upload if needed
        if local_sum != remote_sum:
            commands.append((local_file, remote_filename))

        # Check mode
        if mode and remote_file['mode'] != mode:
            commands.append(_chmod(remote_filename, mode))

        # Check user/group
        if (user and remote_file['user'] != user) or (group and remote_file['group'] != group):
            commands.append(_chown(remote_filename, user, group))

    return commands


@operation
def template(state, host, template_filename, remote_filename, **data):
    '''Generate a template and write it to the remote system.'''
    # Load the template from file
    template_file = open(path.join(state.deploy_dir, template_filename), 'r')
    template = Template(template_file.read())

    # Ensure host is always available inside templates
    data['host'] = host

    # Render and make file-like it's output
    output = template.render(data)
    output_file = StringIO(output)

    local_sum = get_file_sha1(output_file)
    remote_sum = host.sha1_file(remote_filename)

    if local_sum != remote_sum:
        return [(output_file, remote_filename)]


@operation
def file(state, host, name, present=True, user=None, group=None, mode=None, touch=False):
    '''Manage the state of files.'''
    info = host.file(name)
    commands = []

    # It's a directory?!
    if info is False:
        raise OperationException('{0} is a directory'.format(name))

    # Doesn't exist & we want it
    if info is None and present:
        commands.append('touch {0}'.format(name))
        if mode:
            commands.append(_chmod(name, mode))
        if user or group:
            commands.append(_chown(name, user, group))

    # It exists and we don't want it
    elif info and not present:
        commands.append('rm -f {0}'.format(name))

    # It exists & we want to ensure its state
    else:
        if touch:
            commands.append('touch {0}'.format(name))

        # Check mode
        if mode and info['mode'] != mode:
            commands.append(_chmod(name, mode))

        # Check user/group
        if (user and info['user'] != user) or (group and info['group'] != group):
            commands.append(_chown(name, user, group))

    return commands


@operation
def directory(state, host, name, present=True, user=None, group=None, mode=None, recursive=False):
    '''Manage the state of directories.'''
    info = host.directory(name)
    commands = []

    # It's a file?!
    if info is False:
        raise OperationException('{0} is a file'.format(name))

    # Doesn't exist & we want it
    if info is None and present:
        commands.append('mkdir -p {0}'.format(name))
        if mode:
            commands.append(_chmod(name, mode, recursive=recursive))
        if user or group:
            commands.append(_chown(name, user, group, recursive=recursive))

    # It exists and we don't want it
    elif not present:
        commands.append('rm -rf {0}'.format(name))

    # It exists & we want to ensure its state
    else:
        # Check mode
        if mode and info['mode'] != mode:
            commands.append(_chmod(name, mode, recursive=recursive))

        # Check user/group
        if (user and info['user'] != user) or (group and info['group'] != group):
            commands.append(_chown(name, user, group, recursive=recursive))

    return commands
