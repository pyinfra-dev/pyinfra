# pyinfra
# File: pyinfra/modules/files.py
# Desc: manage files/templates <> server

'''
The files module handles filesystem state, file uploads and template generation.
'''

from __future__ import unicode_literals

import sys
from os import path, walk
from datetime import timedelta

import six
from jinja2 import UndefinedError

from pyinfra.api import operation, OperationError
from pyinfra.api.util import get_file_sha1, get_template

from .util.files import chmod, chown, ensure_mode_int, sed_replace


@operation(pipeline_facts={
    'file': 'destination'
})
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

    commands = []

    # Get destination info
    info = host.fact.file(destination)

    # Destination is a directory?
    if info is False:
        raise OperationError(
            'Destination {0} already exists and is not a file'.format(destination)
        )

    # Do we download the file? Force by default
    download = force

    # Doesn't exist, lets download it
    if info is None:
        download = True

    # Destination file exists & cache_time: check when the file was last modified,
    # download if old
    elif cache_time:
        # Time on files is not tz-aware, and will be the same tz as the server's time,
        # so we can safely remove the tzinfo from host.fact.date before comparison.
        cache_time = host.fact.date.replace(tzinfo=None) - timedelta(seconds=cache_time)
        if info['mtime'] and info['mtime'] > cache_time:
            download = True

    # If we download, always do user/group/mode as SSH user may be different
    if download:
        commands.append('wget -q {0} -O {1}'.format(source_url, destination))

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
    + line: string or regex matching the target line
    + present: whether the line should be in the file
    + replace: text to replace entire matching lines when ``present=True``
    + flags: list of flags to pass to sed when replacing/deleting

    Note on regex matching:
        unless line matches a line (starts with ^, ends $), pyinfra will wrap it such that
        it does, like: ``^.*LINE*.$``. This means we don't swap parts of lines out. To use
        more involved examples, see ``files.replace``.
    '''

    match_line = line

    # Ensure we're matching a whole ^line$
    if not match_line.startswith('^'):
        match_line = '^.*{0}'.format(match_line)

    if not match_line.endswith('$'):
        match_line = '{0}.*$'.format(match_line)

    # Is there a matching line in this file?
    present_lines = host.fact.find_in_file(name, match_line)
    commands = []

    # If replace present, use that over the matching line
    if replace:
        line = replace
    # We must provide some kind of replace to sed_replace_command below
    else:
        replace = ''

    # Save commands for re-use in dynamic script when file not present at fact stage
    echo_command = 'echo "{0}" >> {1}'.format(line, name)
    sed_replace_command = sed_replace(state, name, match_line, replace, flags=flags)

    # No line and we want it, append it
    if not present_lines and present:
        # If the file does not exist - it *might* be created, so we handle it dynamically
        # with a little script.
        if present_lines is None:
            commands.append('''
                # If the file now exists
                if [ -f "{target}" ]; then
                    # Grep for the line, sed if matches
                    (grep "{match_line}" "{target}" && {sed_replace_command}) || \
                    # Else echo
                    {echo_command}

                # No file, just echo
                else
                    {echo_command}
                fi
            '''.format(
                target=name,
                match_line=match_line,
                echo_command=echo_command,
                sed_replace_command=sed_replace_command
            ))

        # Otherwise the file exists and there is no matching line, so append it
        else:
            commands.append(echo_command)

    # Line(s) exists and we want to remove them, replace with nothing
    elif present_lines and not present:
        commands.append(sed_replace(state, name, match_line, '', flags=flags))

    # Line(s) exists and we have want to ensure they're correct
    elif present_lines and present:
        # If any of lines are different, sed replace them
        if replace and any(line != replace for line in present_lines):
            commands.append(sed_replace_command)

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

    return [sed_replace(state, name, match, replace, flags=flags)]


@operation(pipeline_facts={
    'find_files': 'destination'
})
def sync(state, host, source, destination, user=None, group=None, mode=None, delete=False):
    '''
    Syncs a local directory with a remote one, with delete support. Note that delete will
    remove extra files on the remote side, but not extra directories.

    + source: local directory to sync
    + destination: remote directory to sync to
    + user: user to own the files and directories
    + group: group to own the files and directories
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
    commands.extend(directory(
        state, host, destination,
        user=user, group=group
    ))

    # Ensure any remote dirnames
    for dirname in ensure_dirnames:
        commands.extend(directory(
            state, host,
            '{0}/{1}'.format(destination, dirname),
            user=user, group=group
        ))

    # Put each file combination
    for local_filename, remote_filename in put_files:
        commands.extend(put(
            state, host,
            local_filename, remote_filename,
            user=user, group=group, mode=mode,
            add_deploy_dir=False
        ))

    # Delete any extra files
    if delete:
        remote_filenames = set(host.fact.find_files(destination) or [])
        wanted_filenames = set([remote_filename for _, remote_filename in put_files])
        files_to_delete = remote_filenames - wanted_filenames
        for filename in files_to_delete:
            commands.extend(file(filename, present=False))

    return commands


@operation(pipeline_facts={
    'file': 'remote_filename',
    'sha1_file': 'remote_filename'
})
def put(
    state, host, local_filename, remote_filename,
    user=None, group=None, mode=None, add_deploy_dir=True
):
    '''
    Copy a local file to the remote system.

    + local_filename: local filename
    + remote_filename: remote filename
    + user: user to own the files
    + group: group to own the files
    + mode: permissions of the files
    '''

    # Upload IO objects as-is
    if hasattr(local_filename, 'read'):
        local_file = local_filename

    # Assume string filename
    else:
        # Add deploy directory?
        if add_deploy_dir and state.deploy_dir:
            local_filename = path.join(state.deploy_dir, local_filename)

        local_file = open(local_filename)

    mode = ensure_mode_int(mode)
    remote_file = host.fact.file(remote_filename)
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
        local_sum = get_file_sha1(local_filename)
        remote_sum = host.fact.sha1_file(remote_filename)

        # Check sha1sum, upload if needed
        if local_sum != remote_sum:
            commands.append((local_file, remote_filename))

            if user or group:
                commands.append(chown(remote_filename, user, group))

            if mode:
                commands.append(chmod(remote_filename, mode))

        else:
            # Check mode
            if mode and remote_file['mode'] != mode:
                commands.append(chmod(remote_filename, mode))

            # Check user/group
            if (
                (user and remote_file['user'] != user)
                or (group and remote_file['group'] != group)
            ):
                commands.append(chown(remote_filename, user, group))

    return commands


@operation
def template(
    state, host, template_filename, remote_filename,
    user=None, group=None, mode=None, **data
):
    '''
    Generate a template and write it to the remote system.

    + template_filename: local template filename
    + remote_filename: remote filename
    + user: user to own the files
    + group: group to own the files
    + mode: permissions of the files
    '''

    if state.deploy_dir:
        template_filename = path.join(state.deploy_dir, template_filename)

    # Load the template into memory
    template = get_template(template_filename)

    # Ensure host is always available inside templates
    data['host'] = host
    data['inventory'] = state.inventory

    # Render and make file-like it's output
    try:
        output = template.render(data)
    except UndefinedError as e:
        _, _, trace = sys.exc_info()

        # Jump through to the *second last* traceback, which contains the line number
        # of the error within the in-memory Template object
        while trace.tb_next:
            if trace.tb_next.tb_next:
                trace = trace.tb_next
            else:
                break

        line_number = trace.tb_frame.f_lineno

        # Quickly read the line in question and one above/below for nicer debugging
        template_lines = open(template_filename).readlines()
        template_lines = [line.strip() for line in template_lines]
        relevant_lines = template_lines[max(line_number - 2, 0):line_number + 1]

        raise OperationError('Error in template: {0} (L{1}): {2}\n...\n{3}\n...'.format(
            template_filename, line_number, e, '\n'.join(relevant_lines)
        ))

    output_file = six.StringIO(output)

    # Pass to the put function
    return put(
        state, host,
        output_file, remote_filename,
        user=user, group=group, mode=mode,
        add_deploy_dir=False
    )


@operation(pipeline_facts={
    'link': 'name'
})
def link(
    state, host, name, source=None, present=True, symbolic=True
):
    '''
    Manage the state of links.

    + name: the name of the link
    + source: the file/directory the link points to
    + present: whether the link should exist
    + symbolic: whether to make a symbolic link (vs hard link)

    Source changes:
        If the link exists and points to a different source, pyinfra will remove it and
        recreate a new one pointing to then new source.
    '''

    if present and not source:
        raise OperationError('If present is True source must be provided')

    info = host.fact.link(name)
    commands = []

    # Not a link?
    if info is False:
        raise OperationError('{0} exists and is not a link'.format(name))

    add_cmd = 'ln{0} {1} {2}'.format(
        ' -s' if symbolic else '',
        source, name
    )

    remove_cmd = 'rm -f {0}'.format(name)

    # No link and we want it
    if info is None and present:
        commands.append(add_cmd)

    # It exists and we don't want it
    elif info and not present:
        commands.append(remove_cmd)

    # Exists and want to ensure it's state
    elif info and present:
        # If the source is wrong, remove & recreate the link
        if info['link_target'] != source:
            commands.extend((
                remove_cmd,
                add_cmd
            ))

    return commands


@operation(pipeline_facts={
    'file': 'name'
})
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
    + mode: permissions of the files as an integer, eg: 755
    + touch: whether to touch the file
    '''

    mode = ensure_mode_int(mode)
    info = host.fact.file(name)
    commands = []

    # Not a file?!
    if info is False:
        raise OperationError('{0} exists and is not a file'.format(name))

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
    elif info and present:
        if touch:
            commands.append('touch {0}'.format(name))

        # Check mode
        if mode and info['mode'] != mode:
            commands.append(chmod(name, mode))

        # Check user/group
        if (user and info['user'] != user) or (group and info['group'] != group):
            commands.append(chown(name, user, group))

    return commands


@operation(pipeline_facts={
    'directory': 'name'
})
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

    mode = ensure_mode_int(mode)
    info = host.fact.directory(name)
    commands = []

    # Not a directory?!
    if info is False:
        raise OperationError('{0} exists and is not a directory'.format(name))

    # Doesn't exist & we want it
    if info is None and present:
        commands.append('mkdir -p {0}'.format(name))
        if mode:
            commands.append(chmod(name, mode, recursive=recursive))
        if user or group:
            commands.append(chown(name, user, group, recursive=recursive))

    # It exists and we don't want it
    elif info and not present:
        commands.append('rm -rf {0}'.format(name))

    # It exists & we want to ensure its state
    elif info and present:
        # Check mode
        if mode and info['mode'] != mode:
            commands.append(chmod(name, mode, recursive=recursive))

        # Check user/group
        if (user and info['user'] != user) or (group and info['group'] != group):
            commands.append(chown(name, user, group, recursive=recursive))

    return commands
