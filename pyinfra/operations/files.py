'''
The files module handles filesystem state, file uploads and template generation.
'''

from __future__ import unicode_literals

import posixpath
import sys
import traceback

from datetime import timedelta
from fnmatch import fnmatch
from os import makedirs, path as os_path, walk

import six

from jinja2 import TemplateRuntimeError, TemplateSyntaxError, UndefinedError

from pyinfra import logger
from pyinfra.api import (
    FileDownloadCommand,
    FileUploadCommand,
    operation,
    OperationError,
    OperationTypeError,
    QuoteString,
    RsyncCommand,
    StringCommand,
)
from pyinfra.api.command import make_formatted_string_command
from pyinfra.api.util import (
    get_file_sha1,
    get_path_permissions_mode,
    get_template,
    memoize,
)
from pyinfra.facts.files import (
    Directory,
    File,
    FindFiles,
    FindInFile,
    Link,
    Md5File,
    Sha1File,
    Sha256File,
)
from pyinfra.facts.server import Date, Which

from .util.compat import fspath
from .util.files import (
    chmod,
    chown,
    ensure_mode_int,
    ensure_whole_line_match,
    get_timestamp,
    sed_replace,
)


@operation(pipeline_facts={
    'file': 'dest',
})
def download(
    src, dest,
    user=None, group=None, mode=None, cache_time=None, force=False,
    sha256sum=None, sha1sum=None, md5sum=None,
    state=None, host=None,
):
    '''
    Download files from remote locations using curl or wget.

    + src: source URL of the file
    + dest: where to save the file
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
            name='Download the Docker repo file',
            src='https://download.docker.com/linux/centos/docker-ce.repo',
            dest='/etc/yum.repos.d/docker-ce.repo',
        )
    '''

    info = host.get_fact(File, path=dest)
    # Destination is a directory?
    if info is False:
        raise OperationError(
            'Destination {0} already exists and is not a file'.format(dest),
        )

    # Do we download the file? Force by default
    download = force

    # Doesn't exist, lets download it
    if info is None:
        download = True

    # Destination file exists & cache_time: check when the file was last modified,
    # download if old
    else:
        if cache_time:
            # Time on files is not tz-aware, and will be the same tz as the server's time,
            # so we can safely remove the tzinfo from the Date fact before comparison.
            cache_time = host.get_fact(Date).replace(tzinfo=None) - timedelta(seconds=cache_time)
            if info['mtime'] and info['mtime'] < cache_time:
                download = True

        if sha1sum:
            if sha1sum != host.get_fact(Sha1File, path=dest):
                download = True

        if sha256sum:
            if sha256sum != host.get_fact(Sha256File, path=dest):
                download = True

        if md5sum:
            if md5sum != host.get_fact(Md5File, path=dest):
                download = True

    # If we download, always do user/group/mode as SSH user may be different
    if download:
        curl_command = make_formatted_string_command(
            'curl -sSLf {0} -o {1}',
            QuoteString(src),
            QuoteString(dest),
        )
        wget_command = make_formatted_string_command(
            'wget -q {0} -O {1} || ( rm -f {1} ; exit 1 )',
            QuoteString(src),
            QuoteString(dest),
        )

        if host.get_fact(Which, command='curl'):
            yield curl_command
        elif host.get_fact(Which, command='wget'):
            yield wget_command
        else:
            yield '( {0} ) || ( {1} )'.format(curl_command, wget_command)

        if user or group:
            yield chown(dest, user, group)

        if mode:
            yield chmod(dest, mode)

        if sha1sum:
            yield make_formatted_string_command((
                '(( sha1sum {0} 2> /dev/null || shasum {0} || sha1 {0} ) | grep {1} ) '
                '|| ( echo {2} && exit 1 )'
            ), QuoteString(dest), sha1sum, QuoteString('SHA1 did not match!'))

        if sha256sum:
            yield make_formatted_string_command((
                '(( sha256sum {0} 2> /dev/null || shasum -a 256 {0} || sha256 {0} ) | grep {1}) '
                '|| ( echo {2} && exit 1 )'
            ), QuoteString(dest), sha256sum, QuoteString('SHA256 did not match!'))

        if md5sum:
            yield make_formatted_string_command((
                '(( md5sum {0} 2> /dev/null || md5 {0} ) | grep {1}) '
                '|| ( echo {2} && exit 1 )'
            ), QuoteString(dest), md5sum, QuoteString('MD5 did not match!'))

    else:
        host.noop('file {0} has already been downloaded'.format(dest))


@operation
def line(
    path, line,
    present=True, replace=None, flags=None, backup=False,
    interpolate_variables=False,
    state=None, host=None,
    assume_present=False,
):
    '''
    Ensure lines in files using grep to locate and sed to replace.

    + path: target remote file to edit
    + line: string or regex matching the target line
    + present: whether the line should be in the file
    + replace: text to replace entire matching lines when ``present=True``
    + flags: list of flags to pass to sed when replacing/deleting
    + backup: whether to backup the file (see below)
    + interpolate_variables: whether to interpolate variables in ``replace``
    + assume_present: whether to assume a matching line already exists in the file

    Regex line matching:
        Unless line matches a line (starts with ^, ends $), pyinfra will wrap it such that
        it does, like: ``^.*LINE.*$``. This means we don't swap parts of lines out. To
        change bits of lines, see ``files.replace``.

    Regex line escaping:
        If matching special characters (eg a crontab line containing *), remember to escape
        it first using Python's ``re.escape``.

    Backup:
        If set to ``True``, any editing of the file will place an old copy with the ISO
        date (taken from the machine running ``pyinfra``) appended as the extension. If
        you pass a string value this will be used as the extension of the backed up file.

    Append:
        If ``line`` is not in the file but we want it (``present`` set to ``True``), then
        it will be append to the end of the file.

    Examples:

    .. code:: python

        # prepare to do some maintenance
        maintenance_line = 'SYSTEM IS DOWN FOR MAINTENANCE'
        files.line(
            name='Add the down-for-maintence line in /etc/motd',
            path='/etc/motd',
            line=maintenance_line,
        )

        # Then, after the mantenance is done, remove the maintenance line
        files.line(
            name='Remove the down-for-maintenance line in /etc/motd',
            path='/etc/motd',
            line=maintenance_line,
            replace='',
            present=False,
        )

        # example where there is '*' in the line
        files.line(
            name='Ensure /netboot/nfs is in /etc/exports',
            path='/etc/exports',
            line=r'/netboot/nfs .*',
            replace='/netboot/nfs *(ro,sync,no_wdelay,insecure_locks,no_root_squash,'
            'insecure,no_subtree_check)',
        )

        files.line(
            name='Ensure myweb can run /usr/bin/python3 without password',
            path='/etc/sudoers',
            line=r'myweb .*',
            replace='myweb ALL=(ALL) NOPASSWD: /usr/bin/python3',
        )

        # example when there are double quotes (")
        line = 'QUOTAUSER=""'
        files.line(
            name='Example with double quotes (")',
            path='/etc/adduser.conf',
            line='^{}$'.format(line),
            replace=line,
        )
    '''

    match_line = ensure_whole_line_match(line)

    # Is there a matching line in this file?
    if assume_present:
        present_lines = [line]
    else:
        present_lines = host.get_fact(FindInFile, path=path, pattern=match_line)

    # If replace present, use that over the matching line
    if replace:
        line = replace
    # We must provide some kind of replace to sed_replace_command below
    else:
        replace = ''

    # Save commands for re-use in dynamic script when file not present at fact stage
    echo_command = make_formatted_string_command(
        'echo {0} >> {1}',
        '"{0}"'.format(line) if interpolate_variables else QuoteString(line),
        QuoteString(path),
    )

    if backup:
        backup_filename = '{0}.{1}'.format(path, get_timestamp())
        echo_command = StringCommand(make_formatted_string_command(
            'cp {0} {1} && ', QuoteString(path), QuoteString(backup_filename),
        ), echo_command)

    sed_replace_command = sed_replace(
        path, match_line, replace,
        flags=flags,
        backup=backup,
        interpolate_variables=interpolate_variables,
    )

    # No line and we want it, append it
    if not present_lines and present:
        # If the file does not exist - it *might* be created, so we handle it
        # dynamically with a little script.
        if present_lines is None:
            yield make_formatted_string_command(
                '''
                    if [ -f '{target}' ]; then
                        ( grep {match_line} '{target}' && \
                        {sed_replace_command}) 2> /dev/null || \
                        {echo_command} ;
                    else
                        {echo_command} ;
                    fi
                ''',
                target=QuoteString(path),
                match_line=QuoteString(match_line),
                echo_command=echo_command,
                sed_replace_command=sed_replace_command,
            )

        # File exists but has no matching lines - append it.
        else:
            # If we're doing replacement, only append if the *replacement* line
            # does not exist (as we are appending the replacement).
            if replace:
                present_lines = host.get_fact(
                    FindInFile,
                    path=path,
                    pattern=ensure_whole_line_match(replace),
                )

            if not present_lines:
                yield echo_command
            else:
                host.noop('line "{0}" exists in {1}'.format(replace or line, path))

    # Line(s) exists and we want to remove them, replace with nothing
    elif present_lines and not present:
        yield sed_replace(
            path, match_line, '',
            flags=flags,
            backup=backup,
            interpolate_variables=interpolate_variables,
        )

    # Line(s) exists and we have want to ensure they're correct
    elif present_lines and present:
        # If any of lines are different, sed replace them
        if replace and any(line != replace for line in present_lines):
            yield sed_replace_command
        else:
            host.noop('line "{0}" exists in {1}'.format(replace or line, path))


@operation
def replace(
    path, match, replace,
    flags=None, backup=False,
    interpolate_variables=False,
    state=None, host=None,
):
    '''
    Replace contents of a file using ``sed``.

    + path: target remote file to edit
    + match: text/regex to match for
    + replace: text to replace with
    + flags: list of flags to pass to sed
    + backup: whether to backup the file (see below)
    + interpolate_variables: whether to interpolate variables in ``replace``

    Backup:
        If set to ``True``, any editing of the file will place an old copy with the ISO
        date (taken from the machine running ``pyinfra``) appended as the extension. If
        you pass a string value this will be used as the extension of the backed up file.

    Example:

    .. code:: python

        files.replace(
            name='Change part of a line in a file',
            path='/etc/motd',
            match='verboten',
            replace='forbidden',
        )
    '''

    existing_lines = host.get_fact(FindInFile, path=path, pattern=match)

    # Only do the replacement if the file does not exist (it may be created earlier)
    # or we have matching lines.
    if existing_lines is None or existing_lines:
        yield sed_replace(
            path, match, replace,
            flags=flags,
            backup=backup,
            interpolate_variables=interpolate_variables,
        )
    else:
        host.noop('string "{0}" does not exist in {1}'.format(match, path))


@operation(pipeline_facts={
    'find_files': 'destination',
})
def sync(
    src, dest,
    user=None, group=None, mode=None, delete=False,
    exclude=None, exclude_dir=None, add_deploy_dir=True,
    state=None, host=None,
):
    '''
    Syncs a local directory with a remote one, with delete support. Note that delete will
    remove extra files on the remote side, but not extra directories.

    + src: local directory to sync
    + dest: remote directory to sync to
    + user: user to own the files and directories
    + group: group to own the files and directories
    + mode: permissions of the files
    + delete: delete remote files not present locally
    + exclude: string or list/tuple of strings to match & exclude files (eg *.pyc)
    + exclude_dir: string or list/tuple of strings to match & exclude directories (eg node_modules)
    + add_deploy_dir: interpret src as relative to deploy directory instead of current directory

    Example:

    .. code:: python

        # Sync local files/tempdir to remote /tmp/tempdir
        files.sync(
            name='Sync a local directory with remote',
            src='files/tempdir',
            dest='/tmp/tempdir',
        )
    '''

    # If we don't enforce the source ending with /, remote_dirpath below might start with
    # a /, which makes the os_path.join cut off the destination bit.
    if not src.endswith(os_path.sep):
        src = '{0}{1}'.format(src, os_path.sep)

    # Add deploy directory?
    if add_deploy_dir and state.deploy_dir:
        src = os_path.join(state.deploy_dir, src)

    # Ensure the source directory exists
    if not os_path.isdir(src):
        raise IOError('No such directory: {0}'.format(src))

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
    for dirpath, dirnames, filenames in walk(src, topdown=True):
        remote_dirpath = dirpath.replace(src, '')

        # Filter excluded dirs
        for child_dir in dirnames:
            child_path = os_path.join(remote_dirpath, child_dir)
            if exclude_dir and any(fnmatch(child_path, match) for match in exclude_dir):
                dirnames.remove(child_dir)

        if remote_dirpath:
            ensure_dirnames.append((remote_dirpath, get_path_permissions_mode(dirpath)))

        for filename in filenames:
            full_filename = os_path.join(dirpath, filename)

            # Should we exclude this file?
            if exclude and any(fnmatch(full_filename, match) for match in exclude):
                continue

            put_files.append((
                # Join local as normal (unix, win)
                full_filename,
                # Join remote as unix like
                '/'.join(
                    item for item in
                    (dest, remote_dirpath, filename)
                    if item
                ),
            ))

    # Ensure the destination directory - if the destination is a link, ensure
    # the link target is a directory.
    dest_to_ensure = dest
    dest_link_info = host.get_fact(Link, path=dest)
    if dest_link_info:
        dest_to_ensure = dest_link_info['link_target']

    yield directory(
        dest_to_ensure,
        user=user, group=group,
        mode=get_path_permissions_mode(src),
        state=state, host=host,
    )

    # Ensure any remote dirnames
    for dirpath, dir_mode in ensure_dirnames:
        yield directory(
            '/'.join((dest, dirpath)),
            user=user, group=group, mode=dir_mode,
            state=state, host=host,
        )

    # Put each file combination
    for local_filename, remote_filename in put_files:
        yield put(
            local_filename, remote_filename,
            user=user, group=group,
            mode=mode or get_path_permissions_mode(local_filename),
            add_deploy_dir=False,
            create_remote_dir=False,  # handled above
            state=state, host=host,
        )

    # Delete any extra files
    if delete:
        remote_filenames = set(host.get_fact(FindFiles, path=dest) or [])
        wanted_filenames = set([remote_filename for _, remote_filename in put_files])
        files_to_delete = remote_filenames - wanted_filenames
        for filename in files_to_delete:
            # Should we exclude this file?
            if exclude and any(fnmatch(filename, match) for match in exclude):
                continue

            yield file(filename, present=False, state=state, host=host)


@memoize
def show_rsync_warning():
    logger.warning('The `files.rsync` operation is in alpha!')


@operation
def rsync(
    src, dest, flags=['-ax', '--delete'],
    state=None, host=None,
):
    '''
    Use ``rsync`` to sync a local directory to the remote system. This operation will actually call
    the ``rsync`` binary on your system.

    .. important::
        The ``files.rsync`` operation is in alpha, and only supported using SSH
        or ``@local`` connectors.

    .. caution::
        When using SSH, the ``files.rsync`` operation only supports the ``sudo`` and ``sudo_user``
        global arguments.
    '''

    show_rsync_warning()

    try:
        host.check_can_rsync()
    except NotImplementedError as e:
        raise OperationError(*e.args)

    yield RsyncCommand(src, dest, flags)


def _create_remote_dir(state, host, remote_filename, user, group):
    # Always use POSIX style path as local might be Windows, remote always *nix
    remote_dirname = posixpath.dirname(remote_filename)
    if remote_dirname:
        yield directory(
            path=remote_dirname,
            user=user, group=group,
            _no_check_owner_mode=True,  # don't check existing user/mode
            _no_fail_on_link=True,  # don't fail if the path is a link
            state=state, host=host,
        )


@operation(pipeline_facts={
    'file': 'src',
    'sha1_file': 'src',
})
def get(
    src, dest,
    add_deploy_dir=True, create_local_dir=False, force=False,
    state=None, host=None,
):
    '''
    Download a file from the remote system.

    + src: the remote filename to download
    + dest: the local filename to download the file to
    + add_deploy_dir: dest is relative to the deploy directory
    + create_local_dir: create the local directory if it doesn't exist
    + force: always download the file, even if the local copy matches

    Note:
        This operation is not suitable for large files as it may involve copying
        the remote file before downloading it.

    Example:

    .. code:: python

        files.get(
            name='Download a file from a remote',
            src='/etc/centos-release',
            dest='/tmp/whocares',
        )
    '''

    if add_deploy_dir and state.deploy_dir:
        dest = os_path.join(state.deploy_dir, dest)

    if create_local_dir:
        local_pathname = os_path.dirname(dest)
        if not os_path.exists(local_pathname):
            makedirs(local_pathname)

    remote_file = host.get_fact(File, path=src)

    # No remote file, so assume exists and download it "blind"
    if not remote_file or force:
        yield FileDownloadCommand(src, dest)

    # No local file, so always download
    elif not os_path.exists(dest):
        yield FileDownloadCommand(src, dest)

    # Remote file exists - check if it matches our local
    else:
        local_sum = get_file_sha1(dest)
        remote_sum = host.get_fact(Sha1File, path=src)

        # Check sha1sum, upload if needed
        if local_sum != remote_sum:
            yield FileDownloadCommand(src, dest)


@operation(pipeline_facts={
    'file': 'dest',
    'sha1_file': 'dest',
})
def put(
    src, dest,
    user=None, group=None, mode=None, add_deploy_dir=True,
    create_remote_dir=True, force=False, assume_exists=False,
    state=None, host=None,
):
    '''
    Upload a local file to the remote system.

    + src: local filename to upload
    + dest: remote filename to upload to
    + user: user to own the files
    + group: group to own the files
    + mode: permissions of the files
    + add_deploy_dir: src is relative to the deploy directory
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
            name='Update the message of the day file',
            src='files/motd',
            dest='/etc/motd',
            mode='644',
        )
    '''

    # Upload IO objects as-is
    if hasattr(src, 'read'):
        local_file = src

    # Assume string filename
    else:
        # Add deploy directory?
        if add_deploy_dir and state.deploy_dir:
            src = os_path.join(state.deploy_dir, src)

        local_file = src

        if not assume_exists and not os_path.isfile(local_file):
            raise IOError('No such file: {0}'.format(local_file))

    mode = ensure_mode_int(mode)
    remote_file = host.get_fact(File, path=dest)

    if create_remote_dir:
        yield _create_remote_dir(state, host, dest, user, group)

    # No remote file, always upload and user/group/mode if supplied
    if not remote_file or force:
        yield FileUploadCommand(local_file, dest)

        if user or group:
            yield chown(dest, user, group)

        if mode:
            yield chmod(dest, mode)

    # File exists, check sum and check user/group/mode if supplied
    else:
        local_sum = get_file_sha1(src)
        remote_sum = host.get_fact(Sha1File, path=dest)

        # Check sha1sum, upload if needed
        if local_sum != remote_sum:
            yield FileUploadCommand(local_file, dest)

            if user or group:
                yield chown(dest, user, group)

            if mode:
                yield chmod(dest, mode)

        else:
            changed = False

            # Check mode
            if mode and remote_file['mode'] != mode:
                yield chmod(dest, mode)
                changed = True

            # Check user/group
            if (
                (user and remote_file['user'] != user)
                or (group and remote_file['group'] != group)
            ):
                yield chown(dest, user, group)
                changed = True

            if not changed:
                host.noop('file {0} is already uploaded'.format(dest))


@operation
def template(
    src, dest,
    user=None, group=None, mode=None, create_remote_dir=True,
    state=None, host=None,
    **data
):
    '''
    Generate a template using jinja2 and write it to the remote system.

    + src: local template filename
    + dest: remote filename
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
            name='Create a templated file',
            src='templates/somefile.conf.j2',
            dest='/etc/somefile.conf',
        )

        files.template(
            name='Create service file',
            src='templates/myweb.service.j2',
            dest='/etc/systemd/system/myweb.service',
            mode='755',
            user='root',
            group='root',
        )

        # Example showing how to pass python variable to template file. You can also
        # use dicts and lists. The .j2 file can use `{{ foo_variable }}` to be interpolated.
        foo_variable = 'This is some foo variable contents'
        foo_dict = {
            "str1": "This is string 1",
            "str2": "This is string 2"
        }
        foo_list = [
            "entry 1",
            "entry 2"
        ]
        files.template(
            name='Create a templated file',
            src='templates/foo.yml.j2',
            dest='/tmp/foo.yml',
            foo_variable=foo_variable,
            foo_dict=foo_dict,
            foo_list=foo_list
        )

    .. code:: yml

        # templates/foo.j2
        name: "{{ foo_variable }}"
        dict_contents:
            str1: "{{ foo_dict.str1 }}"
            str2: "{{ foo_dict.str2 }}"
        list_contents:
        {% for entry in foo_list %}
            - "{{ entry }}"
        {% endfor %}
    '''

    if state.deploy_dir:
        src = os_path.join(state.deploy_dir, src)

    # Ensure host/state/inventory are available inside templates (if not set)
    data.setdefault('host', host)
    data.setdefault('state', state)
    data.setdefault('inventory', state.inventory)

    # Render and make file-like it's output
    try:
        output = get_template(src).render(data)
    except (TemplateRuntimeError, TemplateSyntaxError, UndefinedError) as e:
        trace_frames = traceback.extract_tb(sys.exc_info()[2])
        trace_frames = [
            frame for frame in trace_frames
            if frame[2] in ('template', '<module>', 'top-level template code')
        ]  # thank you https://github.com/saltstack/salt/blob/master/salt/utils/templates.py

        line_number = trace_frames[-1][1]

        # Quickly read the line in question and one above/below for nicer debugging
        with open(src, 'r') as f:
            template_lines = f.readlines()

        template_lines = [line.strip() for line in template_lines]
        relevant_lines = template_lines[max(line_number - 2, 0):line_number + 1]

        raise OperationError('Error in template: {0} (L{1}): {2}\n...\n{3}\n...'.format(
            src, line_number, e, '\n'.join(relevant_lines),
        ))

    output_file = six.StringIO(output)
    # Set the template attribute for nicer debugging
    output_file.template = src

    # Pass to the put function
    yield put(
        output_file, dest,
        user=user, group=group, mode=mode,
        add_deploy_dir=False,
        create_remote_dir=create_remote_dir,
        state=state, host=host,
    )


def _validate_path(path):
    try:
        path = fspath(path)
    except TypeError:
        raise OperationTypeError('`path` must be a string or `os.PathLike` object')


@operation(pipeline_facts={
    'link': 'path',
})
def link(
    path,
    target=None, present=True, assume_present=False,
    user=None, group=None, symbolic=True,
    create_remote_dir=True,
    state=None, host=None,
):
    '''
    Add/remove/update links.

    + path: the name of the link
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
            name='Create link /etc/issue2 that points to /etc/issue',
            path='/etc/issue2',
            target='/etc/issue',
        )


        # complex example demonstrating the assume_present option
        from pyinfra.operations import apt, files

        install_nginx = apt.packages(
            name='Install nginx',
            packages=['nginx'],
        )

        files.link(
            name='Remove default nginx site',
            path='/etc/nginx/sites-enabled/default',
            present=False,
            assume_present=install_nginx.changed,
        )
    '''

    _validate_path(path)

    if present and not target:
        raise OperationError('If present is True target must be provided')

    info = host.get_fact(Link, path=path)

    # Not a link?
    if info is False:
        raise OperationError('{0} exists and is not a link'.format(path))

    add_args = ['ln']
    if symbolic:
        add_args.append('-s')

    add_cmd = StringCommand(' '.join(add_args), QuoteString(target), QuoteString(path))
    remove_cmd = StringCommand('rm', '-f', QuoteString(path))

    # No link and we want it
    if not assume_present and info is None and present:
        if create_remote_dir:
            yield _create_remote_dir(state, host, path, user, group)

        yield add_cmd

        if user or group:
            yield chown(path, user, group, dereference=False)

        host.create_fact(
            Link,
            kwargs={'path': path},
            data={'link_target': target, 'group': group, 'user': user},
        )

    # It exists and we don't want it
    elif (assume_present or info) and not present:
        yield remove_cmd
        host.delete_fact(Link, kwargs={'path': path})

    # Exists and want to ensure it's state
    elif (assume_present or info) and present:
        if assume_present and not info:
            info = {'link_target': None, 'group': None, 'user': None}
            host.create_fact(Link, kwargs={'path': path}, data=info)

        # If we have an absolute path - prepend to any non-absolute values from the fact
        # and/or the source.
        if os_path.isabs(path):
            link_dirname = os_path.dirname(path)

            if not os_path.isabs(target):
                target = os_path.normpath('/'.join((link_dirname, target)))

            if info and not os_path.isabs(info['link_target']):
                info['link_target'] = os_path.normpath(
                    '/'.join((link_dirname, info['link_target'])),
                )

        changed = False

        # If the target is wrong, remove & recreate the link
        if not info or info['link_target'] != target:
            changed = True
            yield remove_cmd
            yield add_cmd
            info['link_target'] = target

        # Check user/group
        if (
            (not info and (user or group))
            or (user and info['user'] != user)
            or (group and info['group'] != group)
        ):
            yield chown(path, user, group, dereference=False)
            changed = True
            if user:
                info['user'] = user
            if group:
                info['group'] = group

        if not changed:
            host.noop('link {0} already exists'.format(path))


@operation(pipeline_facts={
    'file': 'path',
})
def file(
    path,
    present=True, assume_present=False,
    user=None, group=None, mode=None, touch=False,
    create_remote_dir=True,
    state=None, host=None,
):
    '''
    Add/remove/update files.

    + path: name/path of the remote file
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
            name='Create /tmp/secret/file',
            path='/tmp/secret/file',
            mode='600',
            user='root',
            group='root',
            touch=True,
            create_remote_dir=True,
        )
    '''

    _validate_path(path)

    mode = ensure_mode_int(mode)
    info = host.get_fact(File, path=path)

    # Not a file?!
    if info is False:
        raise OperationError('{0} exists and is not a file'.format(path))

    # Doesn't exist & we want it
    if not assume_present and info is None and present:
        if create_remote_dir:
            yield _create_remote_dir(state, host, path, user, group)

        yield StringCommand('touch', QuoteString(path))

        if mode:
            yield chmod(path, mode)
        if user or group:
            yield chown(path, user, group)

        host.create_fact(
            File,
            kwargs={'path': path},
            data={'mode': mode, 'group': group, 'user': user},
        )

    # It exists and we don't want it
    elif (assume_present or info) and not present:
        yield StringCommand('rm', '-f', QuoteString(path))
        host.delete_fact(File, kwargs={'path': path})

    # It exists & we want to ensure its state
    elif (assume_present or info) and present:
        if assume_present and not info:
            info = {'mode': None, 'group': None, 'user': None}
            host.create_fact(File, kwargs={'path': path}, data=info)

        changed = False

        if touch:
            changed = True
            yield StringCommand('touch', QuoteString(path))

        # Check mode
        if mode and (not info or info['mode'] != mode):
            yield chmod(path, mode)
            info['mode'] = mode
            changed = True

        # Check user/group
        if (
            (not info and (user or group))
            or (user and info['user'] != user)
            or (group and info['group'] != group)
        ):
            yield chown(path, user, group)
            changed = True
            if user:
                info['user'] = user
            if group:
                info['group'] = group

        if not changed:
            host.noop('file {0} already exists'.format(path))


@operation(pipeline_facts={
    'directory': 'path',
})
def directory(
    path,
    present=True, assume_present=False,
    user=None, group=None, mode=None, recursive=False,
    _no_check_owner_mode=False,
    _no_fail_on_link=False,
    state=None, host=None,
):
    '''
    Add/remove/update directories.

    + path: path of the remote folder
    + present: whether the folder should exist
    + assume_present: whether to assume the directory exists
    + user: user to own the folder
    + group: group to own the folder
    + mode: permissions of the folder
    + recursive: recursively apply user/group/mode

    Examples:

    .. code:: python

        files.directory(
            name='Ensure the /tmp/dir_that_we_want_removed is removed',
            path='/tmp/dir_that_we_want_removed',
            present=False,
        )

        files.directory(
            name='Ensure /web exists',
            path='/web',
            user='myweb',
            group='myweb',
        )

        # multiple directories
        dirs = ['/netboot/tftp', '/netboot/nfs']
        for dir in dirs:
            files.directory(
                name='Ensure the directory `{}` exists'.format(dir),
                path=dir,
            )
    '''

    _validate_path(path)

    mode = ensure_mode_int(mode)
    info = host.get_fact(Directory, path=path)

    # Not a directory?!
    if info is False:
        if _no_fail_on_link and host.get_fact(Link, path=path):
            host.noop('directory {0} already exists (as a link)'.format(path))
            return
        raise OperationError('{0} exists and is not a directory'.format(path))

    # Doesn't exist & we want it
    if not assume_present and info is None and present:
        yield StringCommand('mkdir', '-p', QuoteString(path))
        if mode:
            yield chmod(path, mode, recursive=recursive)
        if user or group:
            yield chown(path, user, group, recursive=recursive)

        host.create_fact(
            Directory,
            kwargs={'path': path},
            data={'mode': mode, 'group': group, 'user': user},
        )

    # It exists and we don't want it
    elif (assume_present or info) and not present:
        yield StringCommand('rm', '-rf', QuoteString(path))
        host.delete_fact(Directory, kwargs={'path': path})

    # It exists & we want to ensure its state
    elif (assume_present or info) and present:
        if assume_present and not info:
            info = {'mode': None, 'group': None, 'user': None}
            host.create_fact(Directory, kwargs={'path': path}, data=info)

        if _no_check_owner_mode:
            return

        changed = False

        if mode and (not info or info['mode'] != mode):
            yield chmod(path, mode, recursive=recursive)
            info['mode'] = mode
            changed = True

        if (
            (not info and (user or group))
            or (user and info['user'] != user)
            or (group and info['group'] != group)
        ):
            yield chown(path, user, group, recursive=recursive)
            changed = True
            if user:
                info['user'] = user
            if group:
                info['group'] = group

        if not changed:
            host.noop('directory {0} already exists'.format(path))
