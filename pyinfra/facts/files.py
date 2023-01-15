"""
The files facts provide information about the filesystem and it's contents on the target host.
"""

import re
import stat
from datetime import datetime
from typing import List, Tuple

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

# Each item is a map of character to permission octal to be combined, taken from stdlib:
# https://github.com/python/cpython/blob/c1c3be0f9dc414bfae9a5718451ca217751ac687/Lib/stat.py#L128-L154
CHAR_TO_PERMISSION = (
    # User
    {"r": stat.S_IRUSR},
    {"w": stat.S_IWUSR},
    {"x": stat.S_IXUSR, "S": stat.S_ISUID, "s": stat.S_IXUSR | stat.S_ISUID},
    # Group
    {"r": stat.S_IRGRP},
    {"w": stat.S_IWGRP},
    {"x": stat.S_IXGRP, "S": stat.S_ISGID, "s": stat.S_IXGRP | stat.S_ISGID},
    # Other
    {"r": stat.S_IROTH},
    {"w": stat.S_IWOTH},
    {"x": stat.S_IXOTH, "T": stat.S_ISVTX, "t": stat.S_IXOTH | stat.S_ISVTX},
)


def _parse_mode(mode: str) -> int:
    """
    Converts ls mode output (rwxrwxrwx) -> octal permission integer (755).
    """

    out = 0

    for i, char in enumerate(mode):
        for c, m in CHAR_TO_PERMISSION[i].items():
            if char == c:
                out |= m
                break

    return int(oct(out)[2:])


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


class HashFileFactBase(FactBase):
    _raw_cmd: str
    _regexes: Tuple[str, str]

    def __init_subclass__(cls, digits: int, cmds: List[str], **kwargs) -> None:
        super().__init_subclass__(**kwargs)

        raw_hash_cmds = ["%s {0} 2> /dev/null" % cmd for cmd in cmds]
        raw_hash_cmd = " || ".join(raw_hash_cmds)
        cls._raw_cmd = "test -e {0} && ( %s ) || true" % raw_hash_cmd

        assert cls.__name__.endswith("File")
        hash_name = cls.__name__[:-4].upper()
        cls._regexes = (
            # GNU coreutils style:
            r"^([a-fA-F0-9]{%d})\s+%%s$" % digits,
            # BSD style:
            r"^%s\s+\(%%s\)\s+=\s+([a-fA-F0-9]{%d})$" % (hash_name, digits),
        )

    def command(self, path):
        self.path = path
        return make_formatted_string_command(self._raw_cmd, QuoteString(path))

    def process(self, output):
        output = output[0]
        escaped_path = re.escape(self.path)
        for regex in self._regexes:
            matches = re.match(regex % escaped_path, output)
            if matches:
                return matches.group(1)


class Sha1File(HashFileFactBase, digits=40, cmds=["sha1sum", "shasum", "sha1"]):
    """
    Returns a SHA1 hash of a file. Works with both sha1sum and sha1. Returns
    ``None`` if the file doest not exist.
    """


class Sha256File(HashFileFactBase, digits=64, cmds=["sha256sum", "shasum -a 256", "sha256"]):
    """
    Returns a SHA256 hash of a file, or ``None`` if the file does not exist.
    """


class Md5File(HashFileFactBase, digits=32, cmds=["md5sum", "md5"]):
    """
    Returns an MD5 hash of a file, or ``None`` if the file does not exist.
    """


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


class Flags(FactBase):
    """
    Returns a list of the file flags set for the specified file or directory.
    """

    requires_command = "chflags"  # don't try to retrieve them if we can't set them

    def command(self, path):
        return make_formatted_string_command(
            "! test -e {0} || stat -f %Sf {0}",
            QuoteString(path),
        )

    def process(self, output):

        return [flag for flag in output[0].split(",") if len(flag) > 0] if len(output) == 1 else []


MARKER_DEFAULT = "# {mark} PYINFRA BLOCK"
MARKER_BEGIN_DEFAULT = "BEGIN"
MARKER_END_DEFAULT = "END"
EXISTS = "__pyinfra_exists_"
MISSING = "__pyinfra_missing_"


class Block(FactBase):
    """
    Returns a (possibly empty) list of the lines found between the markers.

    .. code:: python

        [
            "xray: one",
            "alpha: two"
        ]

    If the ``path`` doesn't exist
        returns ``None``

    If the ``path`` exists but the markers are not found
        returns ``[]``
    """

    # if markers aren't found, awk will return 0 and produce no output but we need to
    # distinguish between "markers not found" and "markers found but nothing between them"
    # for the former we use the empty list (created the call to default) and for the latter
    # the list with a single empty string.
    default = list

    def command(self, path, marker=None, begin=None, end=None):

        self.path = path
        start = (marker or MARKER_DEFAULT).format(mark=begin or MARKER_BEGIN_DEFAULT)
        end = (marker or MARKER_DEFAULT).format(mark=end or MARKER_END_DEFAULT)
        if start == end:
            raise ValueError(f"delimiters for block must be different but found only '{start}'")

        backstop = make_formatted_string_command(
            "(find {0} -type f > /dev/null && echo {1} || echo {2} )",
            QuoteString(path),
            QuoteString(f"{EXISTS}{path}"),
            QuoteString(f"{MISSING}{path}"),
        )
        # m_f_s_c inserts blanks in unfortunate places, e.g. after first slash
        cmd = make_formatted_string_command(
            f"awk \\'/{end}/{{{{f=0}}}} f; /{start}/{{{{f=1}}}}\\' {{0}} || {backstop}",
            QuoteString(path),
        )
        return cmd

    def process(self, output):
        if output and (output[0] == f"{EXISTS}{self.path}"):
            return []
        if output and (output[0] == f"{MISSING}{self.path}"):
            return None
        return output
