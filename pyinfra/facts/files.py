"""
The files facts provide information about the filesystem and it's contents on the target host.
"""

import re
from datetime import datetime

from pyinfra.api.command import QuoteString, make_formatted_string_command
from pyinfra.api.facts import FactBase
from pyinfra.api.util import try_int

LINUX_STAT_COMMAND = "stat -c 'user=%U group=%G mode=%A atime=%X mtime=%Y ctime=%Z size=%s %N'"
BSD_STAT_COMMAND = "stat -f 'user=%Su group=%Sg mode=%Sp atime=%a mtime=%m ctime=%c size=%z %N%SY'"

STAT_REGEX = (
    r"user=(.*) group=(.*) mode=(.*) "
    r"atime=([0-9]*) mtime=([0-9]*) ctime=([0-9]*) "
    r"size=([0-9]*) (.*)"
)

FLAG_TO_TYPE = {
    "b": "block",
    "c": "character",
    "d": "directory",
    "l": "link",
    "s": "socket",
    "p": "fifo",
    "-": "file",
}

SYMBOL_TO_OCTAL_PERMISSIONS = {
    "rwx": "7",
    "rw-": "6",
    "r-x": "5",
    "r--": "4",
    "-wx": "3",
    "-w-": "2",
    "--x": "1",
}


def _parse_mode(mode):
    """
    Converts ls mode output (rwxrwxrwx) -> integer (755).
    """

    result = ""
    # owner, group, world
    for group in [mode[0:3], mode[3:6], mode[6:9]]:
        if group in SYMBOL_TO_OCTAL_PERMISSIONS:
            result = "{0}{1}".format(result, SYMBOL_TO_OCTAL_PERMISSIONS[group])
        else:
            result = "{0}0".format(result)

    return int(result)


class File(FactBase):
    """
    Returns information about a file on the remote system:

    .. code:: python

        {
            "user": "pyinfra",
            "group": "pyinfra",
            "mode": 644,
            "size": 3928,
        }

    If the path does not exist:
        returns ``None``

    If the path exists but is not a file:
        returns ``False``
    """

    type = "file"

    def command(self, path):
        return make_formatted_string_command(
            (
                # only stat if the path exists (file or symlink)
                "! (test -e {0} || test -L {0} ) || "
                "( {linux_stat_command} {0} 2> /dev/null || {bsd_stat_command} {0} )"
            ),
            QuoteString(path),
            linux_stat_command=LINUX_STAT_COMMAND,
            bsd_stat_command=BSD_STAT_COMMAND,
        )

    def process(self, output):
        match = re.match(STAT_REGEX, output[0])
        if not match:
            return None

        data = {}
        path_type = None

        for key, value in (
            ("user", match.group(1)),
            ("group", match.group(2)),
            ("mode", match.group(3)),
            ("atime", match.group(4)),
            ("mtime", match.group(5)),
            ("ctime", match.group(6)),
            ("size", match.group(7)),
        ):
            if key == "mode":
                path_type = FLAG_TO_TYPE[value[0]]
                value = _parse_mode(value[1:])

            elif key == "size":
                value = try_int(value)

            elif key in ("atime", "mtime", "ctime"):
                value = try_int(value)
                if isinstance(value, int):
                    value = datetime.utcfromtimestamp(value)

            data[key] = value

        if path_type != self.type:
            return False

        if path_type == "link":
            filename = match.group(8)
            filename, target = filename.split(" -> ")
            data["link_target"] = target.strip("'").lstrip("`")

        return data


class Link(File):
    """
    Returns information about a link on the remote system:

    .. code:: python

        {
            "user": "pyinfra",
            "group": "pyinfra",
            "link_target": "/path/to/link/target"
        }

    If the path does not exist:
        returns ``None``

    If the path exists but is not a link:
        returns ``False``
    """

    type = "link"


class Directory(File):
    """
    Returns information about a directory on the remote system:

    .. code:: python

        {
            "user": "pyinfra",
            "group": "pyinfra",
            "mode": 644,
        }

    If the path does not exist:
        returns ``None``

    If the path exists but is not a directory:
        returns ``False``
    """

    type = "directory"


class Socket(File):
    """
    Returns information about a socket on the remote system:

    .. code:: python

        {
            "user": "pyinfra",
            "group": "pyinfra",
        }

    If the path does not exist:
        returns ``None``

    If the path exists but is not a socket:
        returns ``False``
    """

    type = "socket"


class Sha1File(FactBase):
    """
    Returns a SHA1 hash of a file. Works with both sha1sum and sha1. Returns
    ``None`` if the file doest not exist.
    """

    _regexes = [
        r"^([a-zA-Z0-9]{40})\s+%s$",
        r"^SHA1\s+\(%s\)\s+=\s+([a-zA-Z0-9]{40})$",
    ]

    def command(self, path):
        self.path = path
        return make_formatted_string_command(
            (
                "test -e {0} && ( "
                "sha1sum {0} 2> /dev/null || shasum {0} 2> /dev/null || sha1 {0} "
                ") || true"
            ),
            QuoteString(path),
        )

    def process(self, output):
        for regex in self._regexes:
            regex = regex % re.escape(self.path)
            matches = re.match(regex, output[0])
            if matches:
                return matches.group(1)


class Sha256File(FactBase):
    """
    Returns a SHA256 hash of a file, or ``None`` if the file does not exist.
    """

    _regexes = [
        r"^([a-zA-Z0-9]{64})\s+%s$",
        r"^SHA256\s+\(%s\)\s+=\s+([a-zA-Z0-9]{64})$",
    ]

    def command(self, path):
        self.path = path
        return make_formatted_string_command(
            (
                "test -e {0} && ( "
                "sha256sum {0} 2> /dev/null "
                "|| shasum -a 256 {0} 2> /dev/null "
                "|| sha256 {0} "
                ") || true"
            ),
            QuoteString(path),
        )

    def process(self, output):
        for regex in self._regexes:
            regex = regex % re.escape(self.path)
            matches = re.match(regex, output[0])
            if matches:
                return matches.group(1)


class Md5File(FactBase):
    """
    Returns an MD5 hash of a file, or ``None`` if the file does not exist.
    """

    _regexes = [
        r"^([a-zA-Z0-9]{32})\s+%s$",
        r"^SHA256\s+\(%s\)\s+=\s+([a-zA-Z0-9]{32})$",
    ]

    def command(self, path):
        self.path = path
        return make_formatted_string_command(
            "test -e {0} && ( md5sum {0} 2> /dev/null || md5 {0} ) || true",
            QuoteString(path),
        )

    def process(self, output):
        for regex in self._regexes:
            regex = regex % re.escape(self.path)
            matches = re.match(regex, output[0])
            if matches:
                return matches.group(1)


class FindInFile(FactBase):
    """
    Checks for the existence of text in a file using grep. Returns a list of matching
    lines if the file exists, and ``None`` if the file does not.
    """

    def command(self, path, pattern, interpolate_variables=False):
        self.exists_flag = "__pyinfra_exists_{0}".format(path)

        if interpolate_variables:
            pattern = '"{0}"'.format(pattern.replace('"', '\\"'))
        else:
            pattern = QuoteString(pattern)

        return make_formatted_string_command(
            (
                "grep -e {0} {1} 2> /dev/null || "
                "( find {1} -type f > /dev/null && echo {2} || true )"
            ),
            pattern,
            QuoteString(path),
            QuoteString(self.exists_flag),
        )

    def process(self, output):
        # If output is the special string: no matches, so return an empty list;
        # this allows us to differentiate between no matches in an existing file
        # or a file not existing.
        if output and output[0] == self.exists_flag:
            return []

        return output


class FindFilesBase(FactBase):
    abstract = True
    default = list

    @staticmethod
    def process(output):
        return output

    def command(self, path, quote_path=True):
        return make_formatted_string_command(
            "find {0} -type {type_flag} || true",
            QuoteString(path) if quote_path else path,
            type_flag=self.type_flag,
        )


class FindFiles(FindFilesBase):
    """
    Returns a list of files from a start path, recursively using ``find``.
    """

    type_flag = "f"


class FindLinks(FindFilesBase):
    """
    Returns a list of links from a start path, recursively using ``find``.
    """

    type_flag = "l"


class FindDirectories(FindFilesBase):
    """
    Returns a list of directories from a start path, recursively using ``find``.
    """

    type_flag = "d"
