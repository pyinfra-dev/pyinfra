'''
The files module handles filesystem state, file uploads and template generation.
'''

from __future__ import unicode_literals

import posixpath
import sys

from datetime import timedelta
from fnmatch import fnmatch
from os import makedirs, path, walk

import six

from jinja2 import TemplateSyntaxError, UndefinedError

from pyinfra.api import operation, OperationError, OperationTypeError
from pyinfra.api.util import get_file_sha1, get_template

from .util.files import chmod, chown, ensure_mode_int, sed_replace


@operation(pipeline_facts={
    'file': 'destination',
})
def download(
    state, host, source_url, destination,
    user=None, group=None, mode=None, cache_time=None, force=False,
    sha256sum=None, sha1sum=None, md5sum=None,
):
    '''
    Download files from remote locations using curl or wget.

    + source_url: source URL of the file
    + destination: where to save the file
    + user: user to own the files
    + group: group to own the files
    + mode: permissions of the files
    + cache_time: if the file exists already, re-download after this time (in seconds)
    + force: always download the file, even if it already exists
    + sha256sum: sha256 hash to checksum the downloaded file against
    + sha1sum: sha1 hash to checksum the downloaded file against
    + md5sum: md5 hash to checksum the downloaded file against

    Example:

    .. code:: python

        files.download(
            {'Download the Docker repo file'},
            'https://download.docker.com/linux/centos/docker-ce.repo',
            '/etc/yum.repos.d/docker-ce.repo',
        )

    '''

    # Get destination info
    info = host.fact.file(destination)

    # Destination is a directory?
    if info is False:
        raise OperationError(
            'Destination {0} already exists and is not a file'.format(destination),
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
        curl_command = 'curl -sSf {0} -o {1}'.format(source_url, destination)
        wget_command = 'wget -q {0} -O {1} || rm -f {1}; exit 1'.format(
            source_url, destination,
        )

        if host.fact.which('curl'):
            yield curl_command
        elif host.fact.which('wget'):
            yield wget_command
        else:
            yield '({0}) || ({1})'.format(curl_command, wget_command)

        if user or group:
            yield chown(destination, user, group)

        if mode:
            yield chmod(destination, mode)

        if sha1sum:
            yield (
                '((sha1sum {0} 2> /dev/null || sha1 {0}) | grep {1}) '
                '|| (echo "SHA1 did not match!" && exit 1)'
            ).format(destination, sha1sum)

        if sha256sum:
            yield (
                '(sha256sum {0} 2> /dev/null | grep {1}) '
                '|| (echo "SHA256 did not match!" && exit 1)'
            ).format(destination, sha256sum)

        if md5sum:
            yield (
                '((md5sum {0} 2> /dev/null || md5 {0}) | grep {1}) '
                '|| (echo "MD5 did not match!" && exit 1)'
            ).format(destination, md5sum)


@operation
def line(state, host, name, line, present=True, replace=None, flags=None):
    '''
    Ensure lines in files using grep to locate and sed to replace.

    + name: target remote file to edit
    + line: string or regex matching the target line
    + present: whether the line should be in the file
    + replace: text to replace entire matching lines when ``present=True``
    + flags: list of flags to pass to sed when replacing/deleting

    Regex line matching:
        Unless line matches a line (starts with ^, ends $), pyinfra will wrap it such that
        it does, like: ``^.*LINE.*$``. This means we don't swap parts of lines out. To
        change bits of lines, see ``files.replace``.

    Regex line escaping:
        If matching special characters (eg a crontab line containing *), remember to escape
        it first using Python's ``re.escape``.

    Examples:

    .. code:: python

        # prepare to do some maintenance
        maintenance_line = 'SYSTEM IS DOWN FOR MAINTENANCE'
        files.line(
            {'Add the down-for-maintence line in /etc/motd'},
            '/etc/motd',
            maintenance_line,
        )

        # Then, after the mantenance is done, remove the maintenance line
        files.line(
            {'Remove the down-for-maintenance line in /etc/motd'},
            '/etc/motd',
            maintenance_line,
            replace='',
            present=False,
        )

        # example where there is '*' in the line
        files.line(
            {'Ensure /netboot/nfs is in /etc/exports'},
            '/etc/exports',
            r'/netboot/nfs .*',
            replace='/netboot/nfs *(ro,sync,no_wdelay,insecure_locks,no_root_squash,'
            'insecure,no_subtree_check)',
        )

        files.line(
            {'Ensure myweb can run /usr/bin/python3 without password'},
            '/etc/sudoers',
            r'myweb .*',
            replace='myweb ALL=(ALL) NOPASSWD: /usr/bin/python3',
        )

        # example when there are double quotes (")
        line = 'QUOTAUSER=""'
        results = files.line(
            {'Example with double quotes (")'},
            '/etc/adduser.conf',
            '^{}$'.format(line),
            replace=line,
        )
        print(results.changed)

    '''

    match_line = line

    # Ensure we're matching a whole ^line$
    if not match_line.startswith('^'):
        match_line = '^.*{0}'.format(match_line)

    if not match_line.endswith('$'):
        match_line = '{0}.*$'.format(match_line)

    # Is there a matching line in this file?
    present_lines = host.fact.find_in_file(name, match_line)

    # If replace present, use that over the matching line
    if replace:
        line = replace
    # We must provide some kind of replace to sed_replace_command below
    else:
        replace = ''

    # Save commands for re-use in dynamic script when file not present at fact stage
    echo_command = 'echo "{0}" >> {1}'.format(line, name)
    sed_replace_command = sed_replace(
        name, match_line, replace,
        flags=flags,
    )

    # No line and we want it, append it
    if not present_lines and present:
        # If the file does not exist - it *might* be created, so we handle it
        # dynamically with a little script.
        if present_lines is None:
            yield '''
                # If the file now exists
                if [ -f "{target}" ]; then
                    # Grep for the line, sed if matches
                    (grep "{match_line}" "{target}" && {sed_replace_command}) 2> /dev/null || \
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
                sed_replace_command=sed_replace_command,
            )

        # Otherwise the file exists and there is no matching line, so append it
        else:
            yield echo_command

    # Line(s) exists and we want to remove them, replace with nothing
    elif present_lines and not present:
        yield sed_replace(name, match_line, '', flags=flags)

    # Line(s) exists and we have want to ensure they're correct
    elif present_lines and present:
        # If any of lines are different, sed replace them
        if replace and any(line != replace for line in present_lines):
            yield sed_replace_command


@operation
def replace(state, host, name, match, replace, flags=None):
    '''
    A simple shortcut for replacing text in files with sed.

    + name: target remote file to edit
    + match: text/regex to match for
    + replace: text to replace with
    + flags: list of flags to pass to sed

    Example:

    .. code:: python

        files.replace(
            {'Change part of a line in a file'},
            '/etc/motd',
            'verboten',
            'forbidden',
        )
    '''

    yield sed_replace(name, match, replace, flags=flags)


@operation(pipeline_facts={
    'find_files': 'destination',
})
def sync(
    state, host, source, destination,
    user=None, group=None, mode=None, delete=False,
    exclude=None, exclude_dir=None, add_deploy_dir=True,
):
    '''
    Syncs a local directory with a remote one, with delete support. Note that delete will
    remove extra files on the remote side, but not extra directories.

    + source: local directory to sync
    + destination: remote directory to sync to
    + user: user to own the files and directories
    + group: group to own the files and directories
    + mode: permissions of the files
    + delete: delete remote files not present locally
    + exclude: string or list/tuple of strings to match & exclude files (eg *.pyc)
    + exclude_dir: string or list/tuple of strings to match & exclude directories (eg node_modules)

    Example:

    .. code:: python

        # Sync local files/tempdir to remote /tmp/tempdir
        files.sync(
            {'Sync a local directory with remote'},
            'files/tempdir',
            '/tmp/tempdir',
        )
    '''

    # If we don't enforce the source ending with /, remote_dirname below might start with
    # a /, which makes the path.join cut off the destination bit.
    if not source.endswith(path.sep):
        source = '{0}{1}'.format(source, path.sep)

    # Add deploy directory?
    if add_deploy_dir and state.deploy_dir:
        source = path.join(state.deploy_dir, source)

    # Ensure the source directory exists
    if not path.isdir(source):
        raise IOError('No such directory: {0}'.format(source))

    # Ensure exclude is a list/tuple
    if exclude is not None:
        if not isinstance(exclude, (list, tuple)):
            exclude = [exclude]

    # Ensure exclude_dir is a list/tuple
    if exclude_dir is not None:
        if not isinstance(exclude_dir, (list, tuple)):
            exclude_dir = [exclude_dir]

    put_files = []
    ensure_dirnames = []
    for dirname, _, filenames in walk(source):
        remote_dirname = dirname.replace(source, '')

        # Should we exclude this dir?
        if exclude_dir and any(fnmatch(remote_dirname, match) for match in exclude_dir):
            continue

        if remote_dirname:
            ensure_dirnames.append(remote_dirname)

        for filename in filenames:
            full_filename = path.join(dirname, filename)

            # Should we exclude this file?
            if exclude and any(fnmatch(full_filename, match) for match in exclude):
                continue

            put_files.append((
                # Join local as normal (unix, win)
                full_filename,
                # Join remote as unix like
                '/'.join(
                    item for item in
                    (destination, remote_dirname, filename)
                    if item
                ),
            ))

    # Ensure the destination directory
    yield directory(
        state, host, destination,
        user=user, group=group,
    )

    # Ensure any remote dirnames
    for dirname in ensure_dirnames:
        yield directory(
            state, host,
            '/'.join((destination, dirname)),
            user=user, group=group,
        )

    # Put each file combination
    for local_filename, remote_filename in put_files:
        yield put(
            state, host,
            local_filename, remote_filename,
            user=user, group=group, mode=mode,
            add_deploy_dir=False,
        )

    # Delete any extra files
    if delete:
        remote_filenames = set(host.fact.find_files(destination) or [])
        wanted_filenames = set([remote_filename for _, remote_filename in put_files])
        files_to_delete = remote_filenames - wanted_filenames
        for filename in files_to_delete:
            # Should we exclude this file?
            if exclude and any(fnmatch(filename, match) for match in exclude):
                continue

            yield file(state, host, filename, present=False)


def _create_remote_dir(state, host, remote_filename, user, group):
    # Always use POSIX style path as local might be Windows, remote always *nix
    remote_dirname = posixpath.dirname(remote_filename)
    if remote_dirname:
        yield directory(
            state, host, remote_dirname,
            user=user, group=group,
        )


@operation(pipeline_facts={
    'file': 'remote_filename',
    'sha1_file': 'remote_filename',
})
def get(
    state, host, remote_filename, local_filename,
    add_deploy_dir=True, create_local_dir=False, force=False,
):
    '''
    Download a file from the remote system.

    + remote_filename: the remote filename to download
    + local_filename: the local filename to download the file to
    + add_deploy_dir: local_filename is relative to the deploy directory
    + create_local_dir: create the local directory if it doesn't exist
    + force: always download the file, even if the local copy matches

    Note:
        This operation is not suitable for large files as it may involve copying
        the remote file before downloading it.

    Example:

    .. code:: python

        files.get(
            {'Download a file from a remote'},
            '/etc/centos-release',
            '/tmp/whocares',
        )

    '''

    if add_deploy_dir and state.deploy_dir:
        local_filename = path.join(state.deploy_dir, local_filename)

    if create_local_dir:
        local_pathname = path.dirname(local_filename)
        if not path.exists(local_pathname):
            makedirs(local_pathname)

    remote_file = host.fact.file(remote_filename)

    # No remote file, so assume exists and download it "blind"
    if not remote_file or force:
        yield ('download', remote_filename, local_filename)

    # No local file, so always download
    elif not path.exists(local_filename):
        yield ('download', remote_filename, local_filename)

    # Remote file exists - check if it matches our local
    else:
        local_sum = get_file_sha1(local_filename)
        remote_sum = host.fact.sha1_file(remote_filename)

        # Check sha1sum, upload if needed
        if local_sum != remote_sum:
            yield ('download', remote_filename, local_filename)


@operation(pipeline_facts={
    'file': 'remote_filename',
    'sha1_file': 'remote_filename',
})
def put(
    state, host, local_filename, remote_filename,
    user=None, group=None, mode=None, add_deploy_dir=True,
    create_remote_dir=False, force=False, assume_exists=False,
):
    '''
    Upload a local file to the remote system.

    + local_filename: local filename
    + remote_filename: remote filename
    + user: user to own the files
    + group: group to own the files
    + mode: permissions of the files
    + add_deploy_dir: local_filename is relative to the deploy directory
    + create_remote_dir: create the remote directory if it doesn't exist
    + force: always upload the file, even if the remote copy matches
    + assume_exists: whether to assume the local file exists

    ``create_remote_dir``:
        If the remote directory does not exist it will be created using the same
        user & group as passed to ``files.put``. The mode will *not* be copied over,
        if this is required call ``files.directory`` separately.

    Note:
        This operation is not suitable for large files as it may involve copying
        the file before uploading it.

    Examples:

    .. code:: python

        # Note: This requires a 'files/motd' file on the local filesystem
        files.put(
            {'Update the message of the day file'},
            'files/motd',
            '/etc/motd',
            mode='644',
        )

    '''

    # Upload IO objects as-is
    if hasattr(local_filename, 'read'):
        local_file = local_filename

    # Assume string filename
    else:
        # Add deploy directory?
        if add_deploy_dir and state.deploy_dir:
            local_filename = path.join(state.deploy_dir, local_filename)

        local_file = local_filename

        if not assume_exists and not path.isfile(local_file):
            raise IOError('No such file: {0}'.format(local_file))

    mode = ensure_mode_int(mode)
    remote_file = host.fact.file(remote_filename)

    if create_remote_dir:
        yield _create_remote_dir(state, host, remote_filename, user, group)

    # No remote file, always upload and user/group/mode if supplied
    if not remote_file or force:
        yield ('upload', local_file, remote_filename)

        if user or group:
            yield chown(remote_filename, user, group)

        if mode:
            yield chmod(remote_filename, mode)

    # File exists, check sum and check user/group/mode if supplied
    else:
        local_sum = get_file_sha1(local_filename)
        remote_sum = host.fact.sha1_file(remote_filename)

        # Check sha1sum, upload if needed
        if local_sum != remote_sum:
            yield ('upload', local_file, remote_filename)

            if user or group:
                yield chown(remote_filename, user, group)

            if mode:
                yield chmod(remote_filename, mode)

        else:
            # Check mode
            if mode and remote_file['mode'] != mode:
                yield chmod(remote_filename, mode)

            # Check user/group
            if (
                (user and remote_file['user'] != user)
                or (group and remote_file['group'] != group)
            ):
                yield chown(remote_filename, user, group)


@operation
def template(
    state, host, template_filename, remote_filename,
    user=None, group=None, mode=None, create_remote_dir=False,
    **data
):
    '''
    Generate a template using jinja2 and write it to the remote system.

    + template_filename: local template filename
    + remote_filename: remote filename
    + user: user to own the files
    + group: group to own the files
    + mode: permissions of the files
    + create_remote_dir: create the remote directory if it doesn't exist

    ``create_remote_dir``:
        If the remote directory does not exist it will be created using the same
        user & group as passed to ``files.put``. The mode will *not* be copied over,
        if this is required call ``files.directory`` separately.

    Notes:
       Common convention is to store templates in a "templates" directory and
       have a filename suffix with '.j2' (for jinja2).

       For information on the template syntax, see
       `the jinja2 docs <https://jinja.palletsprojects.com>`_.

    Examples:

    .. code:: python

        files.template(
            {'Create a templated file'},
            'templates/somefile.conf.j2',
            '/etc/somefile.conf',
        )

        files.template(
            {'Create service file'},
            'templates/myweb.service.j2',
            '/etc/systemd/system/myweb.service',
            mode='755',
            user='root',
            group='root',
        )

        # Example showing how to pass python variable to template file.
        # The .j2 file can use `{{ foo_variable }}` to be interpolated.
        foo_variable = 'This is some foo variable contents'
        files.template(
            {'Create a templated file'},
            'templates/foo.j2',
            '/tmp/foo',
            foo_variable=foo_variable,
        )

    '''

    if state.deploy_dir:
        template_filename = path.join(state.deploy_dir, template_filename)

    # Ensure host is always available inside templates
    data['host'] = host
    data['inventory'] = state.inventory

    # Render and make file-like it's output
    try:
        output = get_template(template_filename).render(data)
    except (TemplateSyntaxError, UndefinedError) as e:
        _, _, trace = sys.exc_info()

        # Jump through to the *second last* traceback, which contains the line number
        # of the error within the in-memory Template object
        while trace.tb_next:
            if trace.tb_next.tb_next:
                trace = trace.tb_next
            else:  # pragma: no cover
                break

        line_number = trace.tb_frame.f_lineno

        # Quickly read the line in question and one above/below for nicer debugging
        with open(template_filename, 'r') as f:
            template_lines = f.readlines()

        template_lines = [line.strip() for line in template_lines]
        relevant_lines = template_lines[max(line_number - 2, 0):line_number + 1]

        raise OperationError('Error in template: {0} (L{1}): {2}\n...\n{3}\n...'.format(
            template_filename, line_number, e, '\n'.join(relevant_lines),
        ))

    output_file = six.StringIO(output)
    # Set the template attribute for nicer debugging
    output_file.template = template_filename

    # Pass to the put function
    yield put(
        state, host,
        output_file, remote_filename,
        user=user, group=group, mode=mode,
        add_deploy_dir=False,
        create_remote_dir=create_remote_dir,
    )


@operation(pipeline_facts={
    'link': 'name',
})
def link(
    state, host, name,
    target=None, present=True, assume_present=False,
    user=None, group=None, symbolic=True,
    create_remote_dir=False,
):
    '''
    Add/remove/update links.

    + name: the name of the link
    + target: the file/directory the link points to
    + present: whether the link should exist
    + assume_present: whether to assume the link exists
    + user: user to own the link
    + group: group to own the link
    + symbolic: whether to make a symbolic link (vs hard link)
    + create_remote_dir: create the remote directory if it doesn't exist

    ``create_remote_dir``:
        If the remote directory does not exist it will be created using the same
        user & group as passed to ``files.put``. The mode will *not* be copied over,
        if this is required call ``files.directory`` separately.

    Source changes:
        If the link exists and points to a different target, pyinfra will remove it and
        recreate a new one pointing to then new target.

    Examples:

    .. code:: python

        # simple example showing how to link to a file
        files.link(
            {'Create link /etc/issue2 that points to /etc/issue'},
            '/etc/issue2',
            '/etc/issue',
        )


        # complex example demonstrating the assume_present option
        from pyinfra.modules import apt, files

        install_nginx = apt.packages(
            {'Install nginx'},
            'nginx',
        )

        files.link(
            {'Remove default nginx site'},
            '/etc/nginx/sites-enabled/default',
            present=False,
            assume_present=install_nginx.changed,
        )

    '''

    if not isinstance(name, six.string_types):
        raise OperationTypeError('Name must be a string')

    if present and not target:
        raise OperationError('If present is True target must be provided')

    info = host.fact.link(name)

    # Not a link?
    if info is False:
        raise OperationError('{0} exists and is not a link'.format(name))

    add_cmd = 'ln{0} {1} {2}'.format(
        ' -s' if symbolic else '',
        target, name,
    )

    remove_cmd = 'rm -f {0}'.format(name)

    # No link and we want it
    if not assume_present and info is None and present:
        if create_remote_dir:
            yield _create_remote_dir(state, host, name, user, group)

        yield add_cmd
        if user or group:
            yield chown(name, user, group, dereference=False)

    # It exists and we don't want it
    elif (assume_present or info) and not present:
        yield remove_cmd

    # Exists and want to ensure it's state
    elif (assume_present or info) and present:
        # If we have an absolute name - prepend to any non-absolute values from the fact
        # and/or the source.
        if path.isabs(name):
            link_dirname = path.dirname(name)

            if not path.isabs(target):
                target = path.normpath('/'.join((link_dirname, target)))

            if info and not path.isabs(info['link_target']):
                info['link_target'] = path.normpath(
                    '/'.join((link_dirname, info['link_target'])),
                )

        # If the target is wrong, remove & recreate the link
        if not info or info['link_target'] != target:
            yield remove_cmd
            yield add_cmd

        # Check user/group
        if (
            (not info and (user or group))
            or (user and info['user'] != user)
            or (group and info['group'] != group)
        ):
            yield chown(name, user, group, dereference=False)


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

    Example:

    .. code:: python

        # Note: The directory /tmp/secret will get created with the default umask.
        files.file(
            {'Create /tmp/secret/file'},
            '/tmp/secret/file',
            mode='600',
            user='root',
            group='root',
            touch=True,
            create_remote_dir=True,
        )
    '''

    if not isinstance(name, six.string_types):
        raise OperationTypeError('Name must be a string')

    mode = ensure_mode_int(mode)
    info = host.fact.file(name)

    # Not a file?!
    if info is False:
        raise OperationError('{0} exists and is not a file'.format(name))

    # Doesn't exist & we want it
    if not assume_present and info is None and present:
        if create_remote_dir:
            yield _create_remote_dir(state, host, name, user, group)

        yield 'touch {0}'.format(name)

        if mode:
            yield chmod(name, mode)
        if user or group:
            yield chown(name, user, group)

    # It exists and we don't want it
    elif (assume_present or info) and not present:
        yield 'rm -f {0}'.format(name)

    # It exists & we want to ensure its state
    elif (assume_present or info) and present:
        if touch:
            yield 'touch {0}'.format(name)

        # Check mode
        if mode and (not info or info['mode'] != mode):
            yield chmod(name, mode)

        # Check user/group
        if (
            (not info and (user or group))
            or (user and info['user'] != user)
            or (group and info['group'] != group)
        ):
            yield chown(name, user, group)


@operation(pipeline_facts={
    'directory': 'name',
})
def directory(
    state, host, name,
    present=True, assume_present=False,
    user=None, group=None, mode=None, recursive=False,
):
    '''
    Add/remove/update directories.

    + name: name/path of the remote folder
    + present: whether the folder should exist
    + assume_present: whether to assume the directory exists
    + user: user to own the folder
    + group: group to own the folder
    + mode: permissions of the folder
    + recursive: recursively apply user/group/mode

    Examples:

    .. code:: python

        files.directory(
            {'Ensure the /tmp/dir_that_we_want_removed is removed'},
            '/tmp/dir_that_we_want_removed',
            present=False,
        )

        files.directory(
            {'Ensure /web exists'},
            '/web',
            user='myweb',
            group='myweb',
        )

        # multiple directories
        dirs = ['/netboot/tftp', '/netboot/nfs']
        for dir in dirs:
            files.directory(
                {'Ensure the directory `{}` exists'.format(dir)},
                dir,
            )

    '''

    if not isinstance(name, six.string_types):
        raise OperationTypeError('Name must be a string')

    mode = ensure_mode_int(mode)
    info = host.fact.directory(name)

    # Not a directory?!
    if info is False:
        raise OperationError('{0} exists and is not a directory'.format(name))

    # Doesn't exist & we want it
    if not assume_present and info is None and present:
        yield 'mkdir -p {0}'.format(name)
        if mode:
            yield chmod(name, mode, recursive=recursive)
        if user or group:
            yield chown(name, user, group, recursive=recursive)

    # It exists and we don't want it
    elif (assume_present or info) and not present:
        yield 'rm -rf {0}'.format(name)

    # It exists & we want to ensure its state
    elif (assume_present or info) and present:
        # Check mode
        if mode and (not info or info['mode'] != mode):
            yield chmod(name, mode, recursive=recursive)

        # Check user/group
        if (
            (not info and (user or group))
            or (user and info['user'] != user)
            or (group and info['group'] != group)
        ):
            yield chown(name, user, group, recursive=recursive)
