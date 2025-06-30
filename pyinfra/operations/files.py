"""
The files operations handles filesystem state, file uploads and template generation.
"""

from __future__ import annotations

import os
import posixpath
import sys
import traceback
from datetime import timedelta
from fnmatch import fnmatch
from io import StringIO
from pathlib import Path
from typing import IO, Any, Union

from jinja2 import TemplateRuntimeError, TemplateSyntaxError, UndefinedError

from pyinfra import host, logger, state
from pyinfra.api import (
    FileDownloadCommand,
    FileUploadCommand,
    OperationError,
    OperationTypeError,
    OperationValueError,
    QuoteString,
    RsyncCommand,
    StringCommand,
    operation,
)
from pyinfra.api.command import make_formatted_string_command
from pyinfra.api.util import (
    get_call_location,
    get_file_io,
    get_file_md5,
    get_file_sha1,
    get_file_sha256,
    get_path_permissions_mode,
    get_template,
    memoize,
)
from pyinfra.facts.files import (
    MARKER_BEGIN_DEFAULT,
    MARKER_DEFAULT,
    MARKER_END_DEFAULT,
    Block,
    Directory,
    File,
    FindFiles,
    FindInFile,
    Flags,
    Link,
    Md5File,
    Sha1File,
    Sha256File,
    Sha384File,
)
from pyinfra.facts.server import Date, Which

from .util import files as file_utils
from .util.files import (
    adjust_regex,
    ensure_mode_int,
    get_timestamp,
    sed_delete,
    sed_replace,
    unix_path_join,
)


@operation()
def download(
    src: str,
    dest: str,
    user: str | None = None,
    group: str | None = None,
    mode: str | None = None,
    cache_time: int | None = None,
    force=False,
    sha384sum: str | None = None,
    sha256sum: str | None = None,
    sha1sum: str | None = None,
    md5sum: str | None = None,
    headers: dict[str, str] | None = None,
    insecure=False,
    proxy: str | None = None,
    temp_dir: str | Path | None = None,
    extra_curl_args: dict[str, str] | None = None,
    extra_wget_args: dict[str, str] | None = None,
):
    """
    Download files from remote locations using ``curl`` or ``wget``.

    + src: source URL of the file
    + dest: where to save the file
    + user: user to own the files
    + group: group to own the files
    + mode: permissions of the files
    + cache_time: if the file exists already, re-download after this time (in seconds)
    + force: always download the file, even if it already exists
    + sha384sum: sha384 hash to checksum the downloaded file against
    + sha256sum: sha256 hash to checksum the downloaded file against
    + sha1sum: sha1 hash to checksum the downloaded file against
    + md5sum: md5 hash to checksum the downloaded file against
    + headers: optional dictionary of headers to set for the HTTP request
    + insecure: disable SSL verification for the HTTP request
    + proxy: simple HTTP proxy through which we can download files, form `http://<yourproxy>:<port>`
    + temp_dir: use this custom temporary directory during the download
    + extra_curl_args: optional dictionary with custom arguments for curl
    + extra_wget_args: optional dictionary with custom arguments for wget

    **Example:**

    .. code:: python

        files.download(
            name="Download the Docker repo file",
            src="https://download.docker.com/linux/centos/docker-ce.repo",
            dest="/etc/yum.repos.d/docker-ce.repo",
        )
    """

    info = host.get_fact(File, path=dest)

    # Destination is a directory?
    if info is False:
        raise OperationError(
            "Destination {0} already exists and is not a file".format(dest),
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
            ctime = host.get_fact(Date).replace(tzinfo=None) - timedelta(seconds=cache_time)
            if info["mtime"] and info["mtime"] < ctime:
                download = True

        if sha1sum:
            if sha1sum != host.get_fact(Sha1File, path=dest):
                download = True

        if sha256sum:
            if sha256sum != host.get_fact(Sha256File, path=dest):
                download = True

        if sha384sum:
            if sha384sum != host.get_fact(Sha384File, path=dest):
                download = True

        if md5sum:
            if md5sum != host.get_fact(Md5File, path=dest):
                download = True

    # If we download, always do user/group/mode as SSH user may be different
    if download:
        temp_file = host.get_temp_filename(
            dest, temp_directory=str(temp_dir) if temp_dir is not None else None
        )

        curl_args: list[Union[str, StringCommand]] = ["-sSLf"]
        wget_args: list[Union[str, StringCommand]] = ["-q"]

        if extra_curl_args:
            for key, value in extra_curl_args.items():
                curl_args.append(StringCommand(key, QuoteString(value)))

        if extra_wget_args:
            for key, value in extra_wget_args.items():
                wget_args.append(StringCommand(key, QuoteString(value)))

        if proxy:
            curl_args.append(f"--proxy {proxy}")
            wget_args.append("-e use_proxy=yes")
            wget_args.append(f"-e http_proxy={proxy}")

        if insecure:
            curl_args.append("--insecure")
            wget_args.append("--no-check-certificate")

        if headers:
            for key, value in headers.items():
                header_arg = StringCommand("--header", QuoteString(f"{key}: {value}"))
                curl_args.append(header_arg)
                wget_args.append(header_arg)

        curl_command = make_formatted_string_command(
            "curl {0} {1} -o {2}",
            StringCommand(*curl_args),
            QuoteString(src),
            QuoteString(temp_file),
        )
        wget_command = make_formatted_string_command(
            "wget {0} {1} -O {2} || ( rm -f {2} ; exit 1 )",
            StringCommand(*wget_args),
            QuoteString(src),
            QuoteString(temp_file),
        )

        if host.get_fact(Which, command="curl"):
            yield curl_command
        elif host.get_fact(Which, command="wget"):
            yield wget_command
        else:
            yield "( {0} ) || ( {1} )".format(curl_command, wget_command)

        yield StringCommand("mv", QuoteString(temp_file), QuoteString(dest))

        if user or group:
            yield file_utils.chown(dest, user, group)

        if mode:
            yield file_utils.chmod(dest, mode)

        if sha1sum:
            yield make_formatted_string_command(
                (
                    "(( sha1sum {0} 2> /dev/null || shasum {0} || sha1 {0} ) | grep {1} ) "
                    "|| ( echo {2} && exit 1 )"
                ),
                QuoteString(dest),
                sha1sum,
                QuoteString("SHA1 did not match!"),
            )

        if sha256sum:
            yield make_formatted_string_command(
                (
                    "(( sha256sum {0} 2> /dev/null || shasum -a 256 {0} || sha256 {0} ) "
                    "| grep {1}) || ( echo {2} && exit 1 )"
                ),
                QuoteString(dest),
                sha256sum,
                QuoteString("SHA256 did not match!"),
            )

        if sha384sum:
            yield make_formatted_string_command(
                (
                    "(( sha384sum {0} 2> /dev/null || shasum -a 384 {0} ) "
                    "| grep {1}) || ( echo {2} && exit 1 )"
                ),
                QuoteString(dest),
                sha384sum,
                QuoteString("SHA384 did not match!"),
            )

        if md5sum:
            yield make_formatted_string_command(
                (
                    "(( md5sum {0} 2> /dev/null || md5 {0} ) | grep {1}) "
                    "|| ( echo {2} && exit 1 )"
                ),
                QuoteString(dest),
                md5sum,
                QuoteString("MD5 did not match!"),
            )
    else:
        host.noop("file {0} has already been downloaded".format(dest))


@operation()
def line(
    path: str,
    line: str,
    present=True,
    replace: str | None = None,
    flags: list[str] | None = None,
    backup=False,
    interpolate_variables=False,
    escape_regex_characters=False,
    ensure_newline=False,
):
    """
    Ensure lines in files using grep to locate and sed to replace.

    + path: target remote file to edit
    + line: string or regex matching the target line
    + present: whether the line should be in the file
    + replace: text to replace entire matching lines when ``present=True``
    + flags: list of flags to pass to sed when replacing/deleting
    + backup: whether to backup the file (see below)
    + interpolate_variables: whether to interpolate variables in ``replace``
    + escape_regex_characters: whether to escape regex characters from the matching line
    + ensure_newline: ensures that the appended line is on a new line

    Regex line matching:
        Unless line matches a line (starts with ^, ends $), pyinfra will wrap it such that
        it does, like: ``^.*LINE.*$``. This means we don't swap parts of lines out. To
        change bits of lines, see ``files.replace``.

    Regex line escaping:
        If matching special characters (eg a crontab line containing ``*``), remember to escape
        it first using Python's ``re.escape``.

    Backup:
        If set to ``True``, any editing of the file will place an old copy with the ISO
        date (taken from the machine running ``pyinfra``) appended as the extension. If
        you pass a string value this will be used as the extension of the backed up file.

    Append:
        If ``line`` is not in the file but we want it (``present`` set to ``True``), then
        it will be append to the end of the file.

    Ensure new line:
        This will ensure that the ``line`` being appended is always on a separate new
        line in case the file doesn't end with a newline character.


    **Examples:**

    .. code:: python

        # prepare to do some maintenance
        maintenance_line = "SYSTEM IS DOWN FOR MAINTENANCE"
        files.line(
            name="Add the down-for-maintenance line in /etc/motd",
            path="/etc/motd",
            line=maintenance_line,
        )

        # Then, after the maintenance is done, remove the maintenance line
        files.line(
            name="Remove the down-for-maintenance line in /etc/motd",
            path="/etc/motd",
            line=maintenance_line,
            replace="",
            present=False,
        )

        # example where there is '*' in the line
        files.line(
            name="Ensure /netboot/nfs is in /etc/exports",
            path="/etc/exports",
            line=r"/netboot/nfs .*",
            replace="/netboot/nfs *(ro,sync,no_wdelay,insecure_locks,no_root_squash,"
            "insecure,no_subtree_check)",
        )

        files.line(
            name="Ensure myweb can run /usr/bin/python3 without password",
            path="/etc/sudoers",
            line=r"myweb .*",
            replace="myweb ALL=(ALL) NOPASSWD: /usr/bin/python3",
        )

        # example when there are double quotes (")
        line = 'QUOTAUSER=""'
        files.line(
            name="Example with double quotes (")",
            path="/etc/adduser.conf",
            line="^{}$".format(line),
            replace=line,
        )
    """

    match_line = adjust_regex(line, escape_regex_characters)
    #
    # if escape_regex_characters:
    #     match_line = re.sub(r"([\.\\\+\*\?\[\^\]\$\(\)\{\}\-])", r"\\\1", match_line)
    #
    # # Ensure we're matching a whole line, note: match may be a partial line so we
    # # put any matches on either side.
    # if not match_line.startswith("^"):
    #     match_line = "^.*{0}".format(match_line)
    # if not match_line.endswith("$"):
    #     match_line = "{0}.*$".format(match_line)

    # Is there a matching line in this file?
    present_lines = host.get_fact(
        FindInFile,
        path=path,
        pattern=match_line,
        interpolate_variables=interpolate_variables,
    )

    # If replace present, use that over the matching line
    if replace:
        line = replace
    # We must provide some kind of replace to sed_replace_command below
    else:
        replace = ""

    # Save commands for re-use in dynamic script when file not present at fact stage
    if ensure_newline:
        echo_command = make_formatted_string_command(
            "( [ $(tail -c1 {1} | wc -l) -eq 0 ] && echo ; echo {0} ) >> {1}",
            '"{0}"'.format(line) if interpolate_variables else QuoteString(line),
            QuoteString(path),
        )
    else:
        echo_command = make_formatted_string_command(
            "echo {0} >> {1}",
            '"{0}"'.format(line) if interpolate_variables else QuoteString(line),
            QuoteString(path),
        )

    if backup:
        backup_filename = "{0}.{1}".format(path, get_timestamp())
        echo_command = StringCommand(
            make_formatted_string_command(
                "cp {0} {1} && ",
                QuoteString(path),
                QuoteString(backup_filename),
            ),
            echo_command,
        )

    sed_replace_command = sed_replace(
        path,
        match_line,
        replace,
        flags=flags,
        backup=backup,
        interpolate_variables=interpolate_variables,
    )

    # No line and we want it, append it
    if not present_lines and present:
        # If we're doing replacement, only append if the *replacement* line
        # does not exist (as we are appending the replacement).
        if replace:
            # Ensure replace explicitly matches a whole line
            replace_line = replace
            if not replace_line.startswith("^"):
                replace_line = f"^{replace_line}"
            if not replace_line.endswith("$"):
                replace_line = f"{replace_line}$"

            present_lines = host.get_fact(
                FindInFile,
                path=path,
                pattern=replace_line,
                interpolate_variables=interpolate_variables,
            )

        if not present_lines:
            yield echo_command
        else:
            host.noop('line "{0}" exists in {1}'.format(replace or line, path))

    # Line(s) exists and we want to remove them
    elif present_lines and not present:
        yield sed_delete(
            path,
            match_line,
            "",
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


@operation()
def replace(
    path: str,
    text: str | None = None,
    replace: str | None = None,
    flags: list[str] | None = None,
    backup=False,
    interpolate_variables=False,
    match=None,  # deprecated
):
    """
    Replace contents of a file using ``sed``.

    + path: target remote file to edit
    + text: text/regex to match against
    + replace: text to replace with
    + flags: list of flags to pass to sed
    + backup: whether to backup the file (see below)
    + interpolate_variables: whether to interpolate variables in ``replace``

    Backup:
        If set to ``True``, any editing of the file will place an old copy with the ISO
        date (taken from the machine running ``pyinfra``) appended as the extension. If
        you pass a string value this will be used as the extension of the backed up file.

    **Example:**

    .. code:: python

        files.replace(
            name="Change part of a line in a file",
            path="/etc/motd",
            text="verboten",
            replace="forbidden",
        )
    """

    if text is None and match:
        text = match
        logger.warning(
            (
                "The `match` argument has been replaced by "
                "`text` in the `files.replace` operation ({0})"
            ).format(get_call_location()),
        )

    if text is None:
        raise TypeError("Missing argument `text` required in `files.replace` operation")

    if replace is None:
        raise TypeError("Missing argument `replace` required in `files.replace` operation")

    existing_lines = host.get_fact(
        FindInFile,
        path=path,
        pattern=text,
        interpolate_variables=interpolate_variables,
    )

    # Only do the replacement if the file does not exist (it may be created earlier)
    # or we have matching lines.
    if existing_lines is None or existing_lines:
        yield sed_replace(
            path,
            text,
            replace,
            flags=flags,
            backup=backup,
            interpolate_variables=interpolate_variables,
        )
    else:
        host.noop('string "{0}" does not exist in {1}'.format(text, path))


@operation()
def sync(
    src: str,
    dest: str,
    user: str | None = None,
    group: str | None = None,
    mode: str | None = None,
    dir_mode: str | None = None,
    delete=False,
    exclude: str | list[str] | tuple[str] | None = None,
    exclude_dir: str | list[str] | tuple[str] | None = None,
    add_deploy_dir=True,
):
    """
    Syncs a local directory with a remote one, with delete support. Note that delete will
    remove extra files on the remote side, but not extra directories.

    + src: local directory to sync
    + dest: remote directory to sync to
    + user: user to own the files and directories
    + group: group to own the files and directories
    + mode: permissions of the files
    + dir_mode: permissions of the directories
    + delete: delete remote files not present locally
    + exclude: string or list/tuple of strings to match & exclude files (eg ``*.pyc``)
    + exclude_dir: string or list/tuple of strings to match & exclude directories (eg node_modules)
    + add_deploy_dir: interpret src as relative to deploy directory instead of current directory

    **Example:**

    .. code:: python

        # Sync local files/tempdir to remote /tmp/tempdir
        files.sync(
            name="Sync a local directory with remote",
            src="files/tempdir",
            dest="/tmp/tempdir",
        )

    Note: ``exclude`` and ``exclude_dir`` use ``fnmatch`` behind the scenes to do the filtering.

    + ``exclude`` matches against the filename.
    + ``exclude_dir`` matches against the path of the directory, relative to ``src``.
      Since fnmatch does not treat path separators (``/`` or ``\\``) as special characters,
      excluding all directories matching a given name, however deep under ``src`` they are,
      can be done for example with ``exclude_dir=["__pycache__", "*/__pycache__"]``

    """
    original_src = src  # Keep a copy to reference in errors
    src = os.path.normpath(src)

    # Add deploy directory?
    if add_deploy_dir and state.cwd:
        src = os.path.join(state.cwd, src)

    # Ensure the source directory exists
    if not os.path.isdir(src):
        raise IOError("No such directory: {0}".format(original_src))

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
    for dirpath, dirnames, filenames in os.walk(src, topdown=True):
        remote_dirpath = Path(os.path.normpath(os.path.relpath(dirpath, src))).as_posix()

        # Filter excluded dirs
        for child_dir in dirnames[:]:
            child_path = os.path.normpath(os.path.join(remote_dirpath, child_dir))
            if exclude_dir and any(fnmatch(child_path, match) for match in exclude_dir):
                dirnames.remove(child_dir)

        if remote_dirpath and remote_dirpath != os.path.curdir:
            ensure_dirnames.append((remote_dirpath, get_path_permissions_mode(dirpath)))

        for filename in filenames:
            full_filename = os.path.join(dirpath, filename)

            # Should we exclude this file?
            if exclude and any(fnmatch(full_filename, match) for match in exclude):
                continue

            remote_full_filename = unix_path_join(
                *[
                    item
                    for item in (dest, remote_dirpath, filename)
                    if item and item != os.path.curdir
                ]
            )
            put_files.append((full_filename, remote_full_filename))

    # Ensure the destination directory - if the destination is a link, ensure
    # the link target is a directory.
    dest_to_ensure = dest
    dest_link_info = host.get_fact(Link, path=dest)
    if dest_link_info:
        dest_to_ensure = dest_link_info["link_target"]

    yield from directory._inner(
        path=dest_to_ensure,
        user=user,
        group=group,
        mode=dir_mode or get_path_permissions_mode(src),
    )

    # Ensure any remote dirnames
    for dir_path_curr, dir_mode_curr in ensure_dirnames:
        yield from directory._inner(
            path=unix_path_join(dest, dir_path_curr),
            user=user,
            group=group,
            mode=dir_mode or dir_mode_curr,
        )

    # Put each file combination
    for local_filename, remote_filename in put_files:
        yield from put._inner(
            src=local_filename,
            dest=remote_filename,
            user=user,
            group=group,
            mode=mode or get_path_permissions_mode(local_filename),
            add_deploy_dir=False,
            create_remote_dir=False,  # handled above
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

            yield from file._inner(path=filename, present=False)


@memoize
def show_rsync_warning() -> None:
    logger.warning("The `files.rsync` operation is in alpha!")


@operation(is_idempotent=False)
def rsync(src: str, dest: str, flags: list[str] | None = None):
    """
    Use ``rsync`` to sync a local directory to the remote system. This operation will actually call
    the ``rsync`` binary on your system.

    .. important::
        The ``files.rsync`` operation is in alpha, and only supported using SSH
        or ``@local`` connectors. When using the SSH connector, rsync will automatically use the
        StrictHostKeyChecking setting, config and known_hosts file (when specified).

    .. caution::
        When using SSH, the ``files.rsync`` operation only supports the ``sudo`` and ``sudo_user``
        global arguments.
    """

    if flags is None:
        flags = ["-ax", "--delete"]
    show_rsync_warning()

    try:
        host.check_can_rsync()
    except NotImplementedError as e:
        raise OperationError(*e.args)

    yield RsyncCommand(src, dest, flags)


def _create_remote_dir(remote_filename, user, group):
    # Always use POSIX style path as local might be Windows, remote always *nix
    remote_dirname = posixpath.dirname(remote_filename)
    if remote_dirname:
        yield from directory._inner(
            path=remote_dirname,
            user=user,
            group=group,
            _no_check_owner_mode=True,  # don't check existing user/mode
            _no_fail_on_link=True,  # don't fail if the path is a link
        )


def _file_equal(local_path: str | IO[Any] | None, remote_path: str) -> bool:
    if local_path is None:
        return False
    for fact, get_sum in [
        (Sha1File, get_file_sha1),
        (Md5File, get_file_md5),
        (Sha256File, get_file_sha256),
    ]:
        remote_sum = host.get_fact(fact, path=remote_path)
        if remote_sum:
            local_sum = get_sum(local_path)
            return local_sum == remote_sum
    return False


@operation(
    # We don't (currently) cache the local state, so there's nothing we can
    # update to flag the local file as present.
    is_idempotent=False,
)
def get(
    src: str,
    dest: str,
    add_deploy_dir=True,
    create_local_dir=False,
    force=False,
):
    """
    Download a file from the remote system.

    + src: the remote filename to download
    + dest: the local filename to download the file to
    + add_deploy_dir: dest is relative to the deploy directory
    + create_local_dir: create the local directory if it doesn't exist
    + force: always download the file, even if the local copy matches

    Note:
        This operation is not suitable for large files as it may involve copying
        the remote file before downloading it.

    **Example:**

    .. code:: python

        files.get(
            name="Download a file from a remote",
            src="/etc/centos-release",
            dest="/tmp/whocares",
        )
    """

    if add_deploy_dir and state.cwd:
        dest = os.path.join(state.cwd, dest)

    if create_local_dir:
        local_pathname = os.path.dirname(dest)
        if not os.path.exists(local_pathname):
            os.makedirs(local_pathname)

    remote_file = host.get_fact(File, path=src)

    # No remote file, so assume exists and download it "blind"
    if not remote_file or force:
        yield FileDownloadCommand(src, dest, remote_temp_filename=host.get_temp_filename(dest))

    # No local file, so always download
    elif not os.path.exists(dest):
        yield FileDownloadCommand(src, dest, remote_temp_filename=host.get_temp_filename(dest))

    # Remote file exists - check if it matches our local
    else:
        # Check hash sum, download if needed
        if not _file_equal(dest, src):
            yield FileDownloadCommand(src, dest, remote_temp_filename=host.get_temp_filename(dest))
        else:
            host.noop("file {0} has already been downloaded".format(dest))


@operation()
def put(
    src: str | IO[Any],
    dest: str,
    user: str | None = None,
    group: str | None = None,
    mode: int | str | bool | None = None,
    add_deploy_dir=True,
    create_remote_dir=True,
    force=False,
    assume_exists=False,
):
    """
    Upload a local file, or file-like object, to the remote system.

    + src: filename or IO-like object to upload
    + dest: remote filename to upload to
    + user: user to own the files
    + group: group to own the files
    + mode: permissions of the files, use ``True`` to copy the local file
    + add_deploy_dir: src is relative to the deploy directory
    + create_remote_dir: create the remote directory if it doesn't exist
    + force: always upload the file, even if the remote copy matches
    + assume_exists: whether to assume the local file exists

    ``dest``:
        If this is a directory that already exists on the remote side, the local
        file will be uploaded to that directory with the same filename.

    ``mode``:
        When set to ``True`` the permissions of the local file are applied to the
        remote file after the upload is complete.  If set to an octal value with
        digits for at least user, group, and other, either as an ``int`` or
        ``str``, those permissions will be used.

    ``create_remote_dir``:
        If the remote directory does not exist it will be created using the same
        user & group as passed to ``files.put``. The mode will *not* be copied over,
        if this is required call ``files.directory`` separately.

    Note:
        This operation is not suitable for large files as it may involve copying
        the file before uploading it.

        Currently, if the mode argument is anything other than a ``bool`` or a full
        octal permission set and the remote file exists, the operation will always
        behave as if the remote file does not match the specified permissions and
        requires a change.

    **Examples:**

    .. code:: python

        files.put(
            name="Update the message of the day file",
            src="files/motd",
            dest="/etc/motd",
            mode="644",
        )

        files.put(
            name="Upload a StringIO object",
            src=StringIO("file contents"),
            dest="/etc/motd",
        )
    """

    # Upload IO objects as-is
    if hasattr(src, "read"):
        local_file = src
        local_sum_path = src

    # Assume string filename
    else:
        assert isinstance(src, (str, Path))
        # Add deploy directory?
        if add_deploy_dir and state.cwd:
            src = os.path.join(state.cwd, src)

        local_file = src

        if os.path.isfile(local_file):
            local_sum_path = local_file
        elif assume_exists:
            local_sum_path = None
        else:
            raise IOError("No such file: {0}".format(local_file))

    if mode is True:
        if isinstance(local_file, str) and os.path.isfile(local_file):
            mode = get_path_permissions_mode(local_file)
        else:
            logger.warning(
                ("No local file exists to get permissions from with `mode=True` ({0})").format(
                    get_call_location(),
                ),
            )
    else:
        mode = ensure_mode_int(mode)

    remote_file = host.get_fact(File, path=dest)

    if not remote_file and bool(host.get_fact(Directory, path=dest)):
        assert isinstance(src, str)
        dest = unix_path_join(dest, os.path.basename(src))
        remote_file = host.get_fact(File, path=dest)

    if create_remote_dir:
        yield from _create_remote_dir(dest, user, group)

    # No remote file, always upload and user/group/mode if supplied
    if not remote_file or force:
        yield FileUploadCommand(
            local_file,
            dest,
            remote_temp_filename=host.get_temp_filename(dest),
        )

        if user or group:
            yield file_utils.chown(dest, user, group)

        if mode:
            yield file_utils.chmod(dest, mode)

    # File exists, check sum and check user/group/mode if supplied
    else:
        if not _file_equal(local_sum_path, dest):
            yield FileUploadCommand(
                local_file,
                dest,
                remote_temp_filename=host.get_temp_filename(dest),
            )

            if user or group:
                yield file_utils.chown(dest, user, group)

            if mode:
                yield file_utils.chmod(dest, mode)

        else:
            changed = False

            # Check mode
            if mode and remote_file["mode"] != mode:
                yield file_utils.chmod(dest, mode)
                changed = True

            # Check user/group
            if (user and remote_file["user"] != user) or (group and remote_file["group"] != group):
                yield file_utils.chown(dest, user, group)
                changed = True

            if not changed:
                host.noop("file {0} is already uploaded".format(dest))


@operation()
def template(
    src: str | IO[Any],
    dest: str,
    user: str | None = None,
    group: str | None = None,
    mode: str | None = None,
    create_remote_dir: bool = True,
    jinja_env_kwargs: dict[str, Any] | None = None,
    **data,
):
    '''
    Generate a template using jinja2 and write it to the remote system.

    + src: template filename or IO-like object
    + dest: remote filename
    + user: user to own the files
    + group: group to own the files
    + mode: permissions of the files
    + create_remote_dir: create the remote directory if it doesn't exist
    + jinja_env_kwargs: keyword arguments to be passed into the jinja Environment()

    ``create_remote_dir``:
        If the remote directory does not exist it will be created using the same
        user & group as passed to ``files.put``. The mode will *not* be copied over,
        if this is required call ``files.directory`` separately.

    ``jinja_env_kwargs``:
        To have more control over how jinja2 renders your template, you can pass
        a dict with arguments that will be passed as keyword args to the jinja2
        `Environment() <https://jinja.palletsprojects.com/en/3.0.x/api/#jinja2.Environment>`_.

    The ``host``, ``state``, and ``inventory`` objects will be automatically passed to the template
    if not set explicitly.

    Notes:
       Common convention is to store templates in a "templates" directory and
       have a filename suffix with '.j2' (for jinja2).

       For information on the template syntax, see
       `the jinja2 docs <https://jinja.palletsprojects.com>`_.

    **Examples:**

    .. code:: python

        files.template(
            name="Create a templated file",
            src="templates/somefile.conf.j2",
            dest="/etc/somefile.conf",
        )

        files.template(
            name="Create service file",
            src="templates/myweb.service.j2",
            dest="/etc/systemd/system/myweb.service",
            mode="755",
            user="root",
            group="root",
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

        template = StringIO("""
        name: "{{ foo_variable }}"
        dict_contents:
            str1: "{{ foo_dict.str1 }}"
            str2: "{{ foo_dict.str2 }}"
        list_contents:
        {% for entry in foo_list %}
            - "{{ entry }}"
        {% endfor %}
        """)

        files.template(
            name="Create a templated file",
            src=template,
            dest="/tmp/foo.yml",
            foo_variable=foo_variable,
            foo_dict=foo_dict,
            foo_list=foo_list
        )

        # Example showing how to use host and inventory in a template file.
        template = StringIO("""
        name: "{{ host.name }}"
        list_contents:
        {% for entry in inventory.groups.my_servers %}
            - "{{ entry }}"
        {% endfor %}
        """)

        files.template(
            name="Create a templated file",
            src=template,
            dest="/tmp/foo.yml"
        )
    '''

    if not hasattr(src, "read") and state.cwd:
        src = os.path.join(state.cwd, src)

    # Ensure host/state/inventory are available inside templates (if not set)
    data.setdefault("host", host)
    data.setdefault("state", state)
    data.setdefault("inventory", state.inventory)

    # Render and make file-like it's output
    try:
        output = get_template(src, jinja_env_kwargs).render(data)
    except (TemplateRuntimeError, TemplateSyntaxError, UndefinedError) as e:
        trace_frames = [
            frame
            for frame in traceback.extract_tb(sys.exc_info()[2])
            if frame[2] in ("template", "<module>", "top-level template code")
        ]  # thank you https://github.com/saltstack/salt/blob/master/salt/utils/templates.py

        line_number = trace_frames[-1][1]

        # Quickly read the line in question and one above/below for nicer debugging
        with get_file_io(src, "r") as f:
            template_lines = f.readlines()

        template_lines = [line.strip() for line in template_lines]
        relevant_lines = template_lines[max(line_number - 2, 0) : line_number + 1]

        raise OperationError(
            "Error in template: {0} (L{1}): {2}\n...\n{3}\n...".format(
                src,
                line_number,
                e,
                "\n".join(relevant_lines),
            ),
        ) from None

    output_file = StringIO(output)
    # Set the template attribute for nicer debugging
    output_file.template = src  # type: ignore[attr-defined]

    # Pass to the put function
    yield from put._inner(
        src=output_file,
        dest=dest,
        user=user,
        group=group,
        mode=mode,
        add_deploy_dir=False,
        create_remote_dir=create_remote_dir,
    )


@operation()
def move(src: str, dest: str, overwrite=False):
    """
    Move remote file/directory/link into remote directory

    + src: remote file/directory to move
    + dest: remote directory to move `src` into
    + overwrite: whether to overwrite dest, if present
    """

    if host.get_fact(File, src) is None:
        raise OperationError("src {0} does not exist".format(src))

    if not host.get_fact(Directory, dest):
        raise OperationError("dest {0} is not an existing directory".format(dest))

    full_dest_path = os.path.join(dest, os.path.basename(src))
    if host.get_fact(File, full_dest_path) is not None:
        if overwrite:
            yield StringCommand("rm", "-rf", QuoteString(full_dest_path))
        else:
            raise OperationError(
                "dest {0} already exists and `overwrite` is unset".format(full_dest_path)
            )

    yield StringCommand("mv", QuoteString(src), QuoteString(dest))


def _validate_path(path):
    try:
        return os.fspath(path)
    except TypeError:
        raise OperationTypeError("`path` must be a string or `os.PathLike` object")


def _raise_or_remove_invalid_path(fs_type, path, force, force_backup, force_backup_dir):
    if force:
        if force_backup:
            backup_path = "{0}.{1}".format(path, get_timestamp())
            if force_backup_dir:
                backup_path = os.path.basename(backup_path)
                backup_path = "{0}/{1}".format(force_backup_dir, backup_path)
            yield StringCommand("mv", QuoteString(path), QuoteString(backup_path))
        else:
            yield StringCommand("rm", "-rf", QuoteString(path))
    else:
        raise OperationError("{0} exists and is not a {1}".format(path, fs_type))


@operation()
def link(
    path: str,
    target: str | None = None,
    present=True,
    user: str | None = None,
    group: str | None = None,
    symbolic=True,
    create_remote_dir=True,
    force=False,
    force_backup=True,
    force_backup_dir: str | None = None,
):
    """
    Add/remove/update links.

    + path: the name of the link
    + target: the file/directory the link points to
    + present: whether the link should exist
    + user: user to own the link
    + group: group to own the link
    + symbolic: whether to make a symbolic link (vs hard link)
    + create_remote_dir: create the remote directory if it doesn't exist
    + force: if the target exists and is not a file, move or remove it and continue
    + force_backup: set to ``False`` to remove any existing non-file when ``force=True``
    + force_backup_dir: directory to move any backup to when ``force=True``

    ``create_remote_dir``:
        If the remote directory does not exist it will be created using the same
        user & group as passed to ``files.put``. The mode will *not* be copied over,
        if this is required call ``files.directory`` separately.

    Source changes:
        If the link exists and points to a different target, pyinfra will remove it and
        recreate a new one pointing to then new target.

    **Examples:**

    .. code:: python

        files.link(
            name="Create link /etc/issue2 that points to /etc/issue",
            path="/etc/issue2",
            target="/etc/issue",
        )
    """

    path = _validate_path(path)

    if present and not target:
        raise OperationError("If present is True target must be provided")

    info = host.get_fact(Link, path=path)

    if info is False:  # not a link
        yield from _raise_or_remove_invalid_path(
            "link",
            path,
            force,
            force_backup,
            force_backup_dir,
        )
        info = None

    add_args = ["ln"]
    if symbolic:
        add_args.append("-s")

    remove_cmd = StringCommand("rm", "-f", QuoteString(path))

    if not present:
        if info:
            yield remove_cmd
        else:
            host.noop("link {link} does not exist")
        return

    assert target is not None  # appease typing QuoteString below
    add_cmd = StringCommand(" ".join(add_args), QuoteString(target), QuoteString(path))

    if info is None:  # create
        if create_remote_dir:
            yield from _create_remote_dir(path, user, group)

        yield add_cmd

        if user or group:
            yield file_utils.chown(path, user, group, dereference=False)

    else:  # edit
        changed = False

        # If the target is wrong, remove & recreate the link
        if not info or info["link_target"] != target:
            changed = True
            yield remove_cmd
            yield add_cmd

        # Check user/group
        if (user and info["user"] != user) or (group and info["group"] != group):
            yield file_utils.chown(path, user, group, dereference=False)
            changed = True

        if not changed:
            host.noop("link {0} already exists".format(path))


@operation()
def file(
    path: str,
    present=True,
    user: str | None = None,
    group: str | None = None,
    mode: int | str | None = None,
    touch=False,
    create_remote_dir=True,
    force=False,
    force_backup=True,
    force_backup_dir: str | None = None,
):
    """
    Add/remove/update files.

    + path: name/path of the remote file
    + present: whether the file should exist
    + user: user to own the files
    + group: group to own the files
    + mode: permissions of the files as an integer, eg: 755
    + touch: whether to touch the file
    + create_remote_dir: create the remote directory if it doesn't exist
    + force: if the target exists and is not a file, move or remove it and continue
    + force_backup: set to ``False`` to remove any existing non-file when ``force=True``
    + force_backup_dir: directory to move any backup to when ``force=True``

    ``create_remote_dir``:
        If the remote directory does not exist it will be created using the same
        user & group as passed to ``files.put``. The mode will *not* be copied over,
        if this is required call ``files.directory`` separately.

    **Example:**

    .. code:: python

        # Note: The directory /tmp/secret will get created with the default umask.
        files.file(
            name="Create /tmp/secret/file",
            path="/tmp/secret/file",
            mode="600",
            user="root",
            group="root",
            touch=True,
            create_remote_dir=True,
        )
    """

    path = _validate_path(path)

    mode = ensure_mode_int(mode)
    info = host.get_fact(File, path=path)

    if info is False:  # not a file
        yield from _raise_or_remove_invalid_path(
            "file",
            path,
            force,
            force_backup,
            force_backup_dir,
        )
        info = None

    if not present:
        if info:
            yield StringCommand("rm", "-f", QuoteString(path))
        else:
            host.noop("file {0} does not exist")
        return

    if info is None:  # create
        if create_remote_dir:
            yield from _create_remote_dir(path, user, group)

        yield StringCommand("touch", QuoteString(path))

        if mode:
            yield file_utils.chmod(path, mode)
        if user or group:
            yield file_utils.chown(path, user, group)

    else:  # update
        changed = False

        if touch:
            changed = True
            yield StringCommand("touch", QuoteString(path))

        # Check mode
        if mode and (not info or info["mode"] != mode):
            yield file_utils.chmod(path, mode)
            changed = True

        # Check user/group
        if (user and info["user"] != user) or (group and info["group"] != group):
            yield file_utils.chown(path, user, group)
            changed = True

        if not changed:
            host.noop("file {0} already exists".format(path))


@operation()
def directory(
    path: str,
    present=True,
    user: str | None = None,
    group: str | None = None,
    mode: int | str | None = None,
    recursive=False,
    force=False,
    force_backup=True,
    force_backup_dir: str | None = None,
    _no_check_owner_mode=False,
    _no_fail_on_link=False,
):
    """
    Add/remove/update directories.

    + path: path of the remote folder
    + present: whether the folder should exist
    + user: user to own the folder
    + group: group to own the folder
    + mode: permissions of the folder
    + recursive: recursively apply user/group/mode
    + force: if the target exists and is not a file, move or remove it and continue
    + force_backup: set to ``False`` to remove any existing non-file when ``force=True``
    + force_backup_dir: directory to move any backup to when ``force=True``

    **Examples:**

    .. code:: python

        files.directory(
            name="Ensure the /tmp/dir_that_we_want_removed is removed",
            path="/tmp/dir_that_we_want_removed",
            present=False,
        )

        files.directory(
            name="Ensure /web exists",
            path="/web",
            user="myweb",
            group="myweb",
        )

        # Multiple directories
        for dir in ["/netboot/tftp", "/netboot/nfs"]:
            files.directory(
                name="Ensure the directory `{}` exists".format(dir),
                path=dir,
            )
    """

    path = _validate_path(path)

    mode = ensure_mode_int(mode)
    info = host.get_fact(Directory, path=path)

    if info is False:  # not a directory
        if _no_fail_on_link and host.get_fact(Link, path=path):
            host.noop("directory {0} already exists (as a link)".format(path))
            return
        yield from _raise_or_remove_invalid_path(
            "directory",
            path,
            force,
            force_backup,
            force_backup_dir,
        )
        info = None

    if not present:
        if info:
            yield StringCommand("rm", "-rf", QuoteString(path))
        else:
            host.noop("directory {0} does not exist")
        return

    if info is None:  # create
        yield StringCommand("mkdir", "-p", QuoteString(path))
        if mode:
            yield file_utils.chmod(path, mode, recursive=recursive)
        if user or group:
            yield file_utils.chown(path, user, group, recursive=recursive)

    else:  # update
        if _no_check_owner_mode:
            return

        changed = False

        if mode and (not info or info["mode"] != mode):
            yield file_utils.chmod(path, mode, recursive=recursive)
            changed = True

        if (user and info["user"] != user) or (group and info["group"] != group):
            yield file_utils.chown(path, user, group, recursive=recursive)
            changed = True

        if not changed:
            host.noop("directory {0} already exists".format(path))


@operation()
def flags(path: str, flags: list[str] | None = None, present=True):
    """
    Set/clear file flags.

    + path: path of the remote folder
    + flags: a list of the file flags to be set or cleared
    + present: whether the flags should be set or cleared

    **Examples:**

    .. code:: python

        files.flags(
            name="Ensure ~/Library is visible in the GUI",
            path="~/Library",
            flags="hidden",
            present=False
        )

        files.directory(
            name="Ensure no one can change these files",
            path="/something/very/important",
            flags=["uchg", "schg"],
            present=True,
            _sudo=True
        )
    """
    flags = flags or []
    if not isinstance(flags, list):
        flags = [flags]

    if len(flags) == 0:
        host.noop(f"no changes requested to flags for '{path}'")
    else:
        current_set = set(host.get_fact(Flags, path=path))
        to_change = list(set(flags) - current_set) if present else list(current_set & set(flags))

        if len(to_change) > 0:
            prefix = "" if present else "no"
            new_flags = ",".join([prefix + flag for flag in sorted(to_change)])
            yield StringCommand("chflags", new_flags, QuoteString(path))
        else:
            host.noop(
                f'\'{path}\' already has \'{",".join(flags)}\' {"set" if present else "clear"}',
            )


@operation()
def block(
    path: str,
    content: str | list[str] | None = None,
    present=True,
    line: str | None = None,
    backup=False,
    escape_regex_characters=False,
    try_prevent_shell_expansion=False,
    before=False,
    after=False,
    marker: str | None = None,
    begin: str | None = None,
    end: str | None = None,
):
    """
    Ensure content, surrounded by the appropriate markers, is present (or not) in the file.

    + path: target remote file
    + content: what should be present in the file (between markers).
    + present: whether the content should be present in the file
    + before: should the content be added before ``line`` if it doesn't exist
    + after: should the content be added after ``line`` if it doesn't exist
    + line: regex before or after which the content should be added if it doesn't exist.
    + backup: whether to backup the file (see ``files.line``). Default False.
    + escape_regex_characters: whether to escape regex characters from the matching line
    + try_prevent_shell_expansion: tries to prevent shell expanding by values like `$`
    + marker: the base string used to mark the text.  Default is ``# {mark} PYINFRA BLOCK``
    + begin: the value for ``{mark}`` in the marker before the content. Default is ``BEGIN``
    + end: the value for ``{mark}`` in the marker after the content. Default is ``END``

    Content appended if ``line`` not found in the file
        If ``content`` is not in the file but is required (``present=True``) and ``line`` is not
        found in the file, ``content`` (surrounded by markers) will be appended to the file.  The
        file is created if necessary.

    Content prepended or appended if ``line`` not specified
        If ``content`` is not in the file but is required and ``line`` was not provided the content
        will either be  prepended to the file (if both ``before`` and ``after``
        are ``True``) or appended to the file (if both are ``False``).

    Removal ignores ``content`` and ``line``

    Preventing shell expansion works by wrapping the content in '`' before passing to `awk`.
    WARNING: This will break if the content contains raw single quotes.

    **Examples:**

    .. code:: python

        # add entry to /etc/host
        files.block(
            name="add IP address for red server",
            path="/etc/hosts",
            content="10.0.0.1 mars-one",
            before=True,
            regex=".*localhost",
        )

        # have two entries in /etc/host
        files.block(
            name="add IP address for red server",
            path="/etc/hosts",
            content="10.0.0.1 mars-one\\n10.0.0.2 mars-two",
            before=True,
            regex=".*localhost",
        )

        # remove marked entry from /etc/hosts
        files.block(
            name="remove all 10.* addresses from /etc/hosts",
            path="/etc/hosts",
            present=False
        )

        # add out of date warning to web page
        files.block(
            name="add out of date warning to web page",
            path="/var/www/html/something.html",
            content= "<p>Warning: this page is out of date.</p>",
            regex=".*<body>.*",
            after=True
            marker="<!-- {mark} PYINFRA BLOCK -->",
        )

        # put complex alias into .zshrc
        files.block(
            path="/home/user/.zshrc",
            content="eval $(thefuck -a)",
            try_prevent_shell_expansion=True,
            marker="## {mark} ALIASES ##"
        )
    """

    logger.warning("The `files.block` operation is currently in beta!")

    mark_1 = (marker or MARKER_DEFAULT).format(mark=begin or MARKER_BEGIN_DEFAULT)
    mark_2 = (marker or MARKER_DEFAULT).format(mark=end or MARKER_END_DEFAULT)

    # standard awk doesn't have an "in-place edit" option so we write to a tempfile and
    # if edits were successful move to dest i.e. we do: <out_prep> ... do some work ... <real_out>
    q_path = QuoteString(path)
    out_prep = StringCommand('OUT="$(TMPDIR=/tmp mktemp -t pyinfra.XXXXXX)" && ')
    if backup:
        out_prep = StringCommand(
            "cp",
            q_path,
            QuoteString(f"{path}.{get_timestamp()}"),
            "&&",
            out_prep,
        )
    real_out = StringCommand(
        "chmod $(stat -c %a",
        q_path,
        "2>/dev/null || stat -f %Lp",
        q_path,
        ") $OUT && ",
        '(chown $(stat -c "%u:%g"',
        q_path,
        "2>/dev/null || ",
        'stat -f "%u:%g"',
        q_path,
        '2>/dev/null ) $OUT) && mv "$OUT"',
        q_path,
    )

    current = host.get_fact(Block, path=path, marker=marker, begin=begin, end=end)
    cmd = None
    if present:
        if not content:
            raise OperationValueError("'content' must be supplied when 'present' == True")
        if line:
            if before == after:
                raise OperationValueError(
                    "only one of 'before' or 'after' used when 'line` is specified"
                )
        elif before != after:
            raise OperationValueError(
                "'line' must be supplied or 'before' and 'after' must be equal"
            )
        if isinstance(content, str):
            # convert string to list of lines
            content = content.split("\n")
        if try_prevent_shell_expansion and any("'" in line for line in content):
            logger.warning("content contains single quotes, shell expansion prevention may fail")

        the_block = "\n".join([mark_1, *content, mark_2])

        if (current is None) or ((current == []) and (before == after)):
            # a) no file or b) file but no markers and we're adding at start or end. Both use 'cat'
            redirect = ">" if (current is None) else ">>"
            stdin = "- " if ((current == []) and before) else ""
            # here = hex(random.randint(0, 2147483647))
            here = "PYINFRAHERE"
            cmd = StringCommand(
                f"cat {stdin}{redirect}",
                q_path,
                f"<<{here}" if not try_prevent_shell_expansion else f"<<'{here}'",
                f"\n{the_block}\n{here}",
            )
        elif current == []:  # markers not found and have a pattern to match (not start or end)
            assert isinstance(line, str)
            regex = adjust_regex(line, escape_regex_characters)
            print_before = "{ print }" if before else ""
            print_after = "{ print }" if after else ""
            prog = (
                'awk \'BEGIN {x=ARGV[2]; ARGV[2]=""} '
                f"{print_after} f!=1 && /{regex}/ {{ print x; f=1}} "
                f"END {{if (f==0) print ARGV[2] }} {print_before}'"
            )
            cmd = StringCommand(
                out_prep,
                prog,
                q_path,
                f'"{the_block}"' if not try_prevent_shell_expansion else f"'{the_block}'",
                "> $OUT &&",
                real_out,
            )
        else:
            if (len(current) != len(content)) or (
                not all(lines[0] == lines[1] for lines in zip(content, current))
            ):  # marked_block found but text is different
                prog = (
                    'awk \'BEGIN {{f=1; x=ARGV[2]; ARGV[2]=""}}'
                    f"/{mark_1}/ {{print; print x; f=0}} /{mark_2}/ {{print; f=1; next}} f'"
                )
                cmd = StringCommand(
                    out_prep,
                    prog,
                    q_path,
                    (
                        '"' + "\n".join(content) + '"'
                        if not try_prevent_shell_expansion
                        else "'" + "\n".join(content) + "'"
                    ),
                    "> $OUT &&",
                    real_out,
                )
            else:
                host.noop("content already present")

        if cmd:
            yield cmd
    else:  # remove the marked_block
        if content:
            logger.warning("'content' ignored when removing a marked_block")
        if current is None:
            host.noop("no remove required: file did not exist")
        elif current == []:
            host.noop("no remove required: markers not found")
        else:
            cmd = StringCommand(f"awk '/{mark_1}/,/{mark_2}/ {{next}} 1'")
            yield StringCommand(out_prep, cmd, q_path, "> $OUT &&", real_out)
