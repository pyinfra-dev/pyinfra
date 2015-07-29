# pyinfra
# File: pyinfra/modules/files.py
# Desc: manage files/templates <> server

'''
The files module handles filesystem state, file uploads and template generation.

Uses POSIX commands:

+ `touch`, `mkdir`, `chown`, `chmod`, `rm`
'''

from os import path
from cStringIO import StringIO

from jinja2 import Template

from pyinfra import host, state
from pyinfra.api import operation, OperationError
from pyinfra.api.util import get_file_sha1


@operation
def put(local_filename, remote_filename):
    '''Copy a local file to the remote system.'''
    local_file = open(path.join(state.deploy_dir, local_filename), 'r')

    local_sum = get_file_sha1(local_file)
    remote_sum = host.sha1_file(remote_filename)

    if local_sum != remote_sum:
        return [(local_file, remote_filename)]


@operation
def template(template_filename, remote_filename, **data):
    '''Generate a template and write it to the remote system.'''
    # Load the template from file
    template_file = open(path.join(state.deploy_dir, template_filename), 'r')
    template = Template(template_file.read())

    # Render and make file-like it's output
    output = template.render(data)
    output_file = StringIO(output)

    local_sum = get_file_sha1(output_file)
    remote_sum = host.sha1_file(remote_filename)

    if local_sum != remote_sum:
        return [(output_file, remote_filename)]


def _chmod(target, mode, recursive=False):
    return 'chmod {0}{1} {2}'.format(('-R ' if recursive else ''), mode, target)

def _chown(target, user, group, recursive=False):
    if user and group:
        user_group = '{0}:{1}'.format(user, group)
    else:
        user_group = user or group

    return 'chown {0}{1} {2}'.format(('-R ' if recursive else ''), user_group, target)

@operation
def file(name, present=True, user=None, group=None, mode=None, touch=False):
    '''Manage the state of files.'''
    info = host.file(name)
    commands = []

    # It's a directory?!
    if info is False:
        raise OperationError('{0} is a directory'.format(name))

    # Doesn't exist & we want it
    if info is None and present:
        commands.append('touch {0}'.format(name))
        if mode:
            commands.append(_chmod(name, mode))
        if user or group:
            commands.append(_chown(name, user, group))

    # It exists and we don't want it
    elif not present:
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
def directory(name, present=True, user=None, group=None, mode=None, recursive=False):
    '''Manage the state of directories.'''
    info = host.directory(name)
    commands = []

    # It's a file?!
    if info is False:
        raise OperationError('{0} is a file'.format(name))

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
