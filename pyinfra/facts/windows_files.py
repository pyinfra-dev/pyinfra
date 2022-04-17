from pyinfra.api.facts import FactBase

from .util.win_files import parse_win_ls_output


class File(FactBase):
    # Types must match WIN_FLAG_TO_TYPE in .util.win_files.py
    type = "file"
    shell_executable = "ps"

    def command(self, path):
        self.path = path
        return ('if (Test-Path "{0}") {{ Get-ItemProperty -Path "{0}" }}').format(path)

    def process(self, output):
        if len(output) < 7:
            return None

        # Note: The first 7 lines are header lines
        return parse_win_ls_output(output[7], self.type)


class Link(File):
    # Types must match WIN_FLAG_TO_TYPE in .util.win_files.py
    type = "link"


class Directory(File):
    # Types must match WIN_FLAG_TO_TYPE in .util.win_files.py
    type = "directory"


class TempDir(FactBase):
    # Types must match WIN_FLAG_TO_TYPE in .util.win_files.py
    type = "directory"
    shell_executable = "ps"

    def command(self):
        return "[System.IO.Path]::GetTempPath()"

    def process(self, output):
        return output[0]


class Sha1File(FactBase):
    """
    Returns a SHA1 hash of a file.
    """

    shell_executable = "ps"

    def command(self, path):
        return (
            'if (Test-Path "{0}") {{ ' '(Get-FileHash -Algorithm SHA1 "{0}").hash' " }}"
        ).format(path)

    def process(self, output):
        return output[0] if not output else None


class Sha256File(FactBase):
    """
    Returns a SHA256 hash of a file.
    """

    shell_executable = "ps"

    def command(self, path):
        return (
            'if (Test-Path "{0}") {{ ' '(Get-FileHash -Algorithm SHA256 "{0}").hash' " }}"
        ).format(path)

    def process(self, output):
        return output[0] if len(output[0]) > 0 else None


class Md5File(FactBase):
    """
    Returns an MD5 hash of a file.
    """

    shell_executable = "ps"

    def command(self, path):
        return ('if (Test-Path "{0}") {{ ' '(Get-FileHash -Algorithm MD5 "{0}").hash' " }}").format(
            path,
        )

    def process(self, output):
        return output[0] if len(output[0]) > 0 else None
