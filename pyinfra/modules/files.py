# pyinfra
# File: pyinfra/modules/files.py
# Desc: manage files/templates <> server

'''
The files module handles filesystem state, file uploads and template generation.
'''

from os import path, walk
from cStringIO import StringIO

from jinja2 import Template

from pyinfra.api import operation, OperationError
from pyinfra.api.util import get_file_sha1

from .util.files import chmod, chown


def _sed_replace(filename, line, replace, flags=None):
    flags = ''.join(flags) if flags else ''

    return 'sed -i "s/{0}/{1}/{2}" {3}'.format(
        line, replace, flags, filename
    )


@operation
def download(
    state, host, source_url, destination,
    user=None, group=None, mode=None, cache_time=None, force=False
):
    '''
    Download files from remote locations.

    + source_url: source URl of the file
    + destination: where to save the file
    + user: user to own the files
    + group: group to own the files
    + mode: permissions of the files
    + cache_time: if the file exists already, re-download after this time (in s)
    + force: always download the file, even if it already exists
    '''

    # Get destination info
    info = host.file(destination)

    # Destination is a directory?
    if info is False:
        raise OperationError('{0} is a directory'.format(destination))

    # Do we download the file? Force by default
    download = force

    # Doesn't exist, lets download it
    if info is None:
        download = True

    # Destination file exists & cache_time: check when the file was last modified,
    # download if old
    elif cache_time:
        download = True

    # If we download, always do user/group/mode as SSH user may be different
    if download:
        commands = ['wget -q {0} -O {1}'.format(source_url, destination)]

        if user or group:
            commands.append(chown(destination, user, group))

        if mode:
            commands.append(chmod(destination, mode))

        return commands


@operation
def line(state, host, name, line, present=True, replace=None, flags=None):
    '''
    Ensure lines in files using grep to locate and sed to replace.

    + name: target remote file to edit
    + line: string or regex matching the *entire* target line
    + present: whether the line should be in the file
    + replace: text to replace entire matching lines when ``present=True``
    + flags: list of flags to pass to sed when replacing/deleting

    Note:
        if not present, line will have ``^`` & ``$`` wrapped around so when using regex
        the entire line must match (eg ``SELINUX=.*``)
    '''

    match_line = line

    # Ensure we're matching a whole ^line$
    if not match_line.startswith('^'):
        match_line = '^{0}'.format(match_line)

    if not match_line.endswith('$'):
        match_line = '{0}$'.format(match_line)

    # Is there a matching line in this file?
    is_present = host.find_in_file(name, match_line)
    commands = []

    # No line and we want it, append it
    if not is_present and present:
        # If replace present, use that over the matching line
        if replace:
            line = replace

        commands.append('echo "{0}" >> {1}'.format(line, name))

    # Line exists and we have a replacement that *is* different, sed it
    if is_present != replace:
        commands.append(_sed_replace(name, match_line, replace, flags=flags))

    # Line exists and we want to remove it, replace with nothing
    if is_present and not present:
        commands.append(_sed_replace(name, match_line, '', flags=flags))

    return commands


@operation
def replace(state, host, name, match, replace, flags=None):
    '''
    A simple shortcut for replacing text in files with sed.

    + name: target remote file to edit
    + match: text/regex to match for
    + replace: text to replace with
    + flags: list of flaggs to pass to sed
    '''

    return [_sed_replace(name, match, replace, flags=flags)]


@operation
def sync(state, host, source, destination, user=None, group=None, mode=None, delete=False):
    '''
    Syncs a local directory with a remote one, with delete support. Note that delete will
    remove extra files on the remote side, but not extra directories.

    + source: local directory to sync
    + destination: remote directory to sync to
    + user: user to own the files
    + group: group to own the files
    + mode: permissions of the files
    + delete: delete remote files not present locally
    '''

    # If we don't enforce the source ending with /, remote_dirname below might start with
    # a /, which makes the path.join cut off the destination bit.
    if not source.endswith(path.sep):
        source = '{0}{1}'.format(source, path.sep)

    # Source relative to deploy.py
    if state.deploy_dir:
        source = path.join(state.deploy_dir, source)

    put_files = []
    ensure_dirnames = []
    for dirname, _, filenames in walk(source):
        remote_dirname = dirname.replace(source, '')

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
    '''
    Copy a local file to the remote system.

    + local_filename: local filename (or file-like object)
    + remote_filename: remote filename
    + user: user to own the files
    + group: group to own the files
    + mode: permissions of the files
    '''

    # Accept local_filename as a string
    if isinstance(local_filename, basestring):
        if state.deploy_dir and add_deploy_dir:
            local_filename = path.join(state.deploy_dir, local_filename)

        local_file = open(local_filename, 'r')

    # Not a string? Assume file-like object
    else:
        local_file = local_filename

    remote_file = host.file(remote_filename)
    commands = []

    # No remote file, always upload and user/group/mode if supplied
    if not remote_file:
        commands.append((local_file, remote_filename))

        if user or group:
            commands.append(chown(remote_filename, user, group))

        if mode:
            commands.append(chmod(remote_filename, mode))

    # File exists, check sum and check user/group/mode if supplied
    else:
        local_sum = get_file_sha1(local_file)
        remote_sum = host.sha1_file(remote_filename)

        # Check sha1sum, upload if needed
        if local_sum != remote_sum:
            commands.append((local_file, remote_filename))

        # Check mode
        if mode and remote_file['mode'] != mode:
            commands.append(chmod(remote_filename, mode))

        # Check user/group
        if (user and remote_file['user'] != user) or (group and remote_file['group'] != group):
            commands.append(chown(remote_filename, user, group))

    return commands


@operation
def template(
    state, host, template_filename, remote_filename,
    user=None, group=None, mode=None, **data
):
    '''
    Generate a template and write it to the remote system.

    + template_filename: local template filename (or file-like object)
    + remote_filename: remote filename
    + user: user to own the files
    + group: group to own the files
    + mode: permissions of the files
    '''

    if state.deploy_dir:
        template_filename = path.join(state.deploy_dir, template_filename)

    # Accept template_filename as a string or (assumed) file-like object
    if isinstance(template_filename, basestring):
        template_file = open(template_filename, 'r')
    else:
        template_file = template_filename

    # Load the template into memory
    template = Template(template_file.read())

    # Ensure host is always available inside templates
    data['host'] = host

    # Render and make file-like it's output
    output = template.render(data)
    output_file = StringIO(output)

    # Pass to the put function
    return put(
        output_file, remote_filename,
        user=user, group=group, mode=mode,
        add_deploy_dir=False
    )


@operation
def file(
    state, host, name,
    present=True, user=None, group=None, mode=None, touch=False
):
    '''
    Manage the state of files.

    + name: name/path of the remote file
    + present: whether the file should exist
    + user: user to own the files
    + group: group to own the files
    + mode: permissions of the files
    + touch: touch the file
    '''

    info = host.file(name)
    commands = []

    # It's a directory?!
    if info is False:
        raise OperationError('{0} is a directory'.format(name))

    # Doesn't exist & we want it
    if info is None and present:
        commands.append('touch {0}'.format(name))

        if mode:
            commands.append(chmod(name, mode))
        if user or group:
            commands.append(chown(name, user, group))

    # It exists and we don't want it
    elif info and not present:
        commands.append('rm -f {0}'.format(name))

    # It exists & we want to ensure its state
    else:
        if touch:
            commands.append('touch {0}'.format(name))

        # Check mode
        if mode and info['mode'] != mode:
            commands.append(chmod(name, mode))

        # Check user/group
        if (user and info['user'] != user) or (group and info['group'] != group):
            commands.append(chown(name, user, group))

    return commands


@operation
def directory(
    state, host, name,
    present=True, user=None, group=None, mode=None, recursive=False
):
    '''
    Manage the state of directories.

    + name: name/patr of the remote file
    + present: whether the file should exist
    + user: user to own the files
    + group: group to own the files
    + mode: permissions of the files
    + recursive: recursively apply user/group/mode
    '''

    info = host.directory(name)
    commands = []

    # It's a file?!
    if info is False:
        raise OperationError('{0} is a file'.format(name))

    # Doesn't exist & we want it
    if info is None and present:
        commands.append('mkdir -p {0}'.format(name))
        if mode:
            commands.append(chmod(name, mode, recursive=recursive))
        if user or group:
            commands.append(chown(name, user, group, recursive=recursive))

    # It exists and we don't want it
    elif not present:
        commands.append('rm -rf {0}'.format(name))

    # It exists & we want to ensure its state
    else:
        # Check mode
        if mode and info['mode'] != mode:
            commands.append(chmod(name, mode, recursive=recursive))

        # Check user/group
        if (user and info['user'] != user) or (group and info['group'] != group):
            commands.append(chown(name, user, group, recursive=recursive))

    return commands
