from __future__ import unicode_literals

import re

from six.moves import shlex_quote

from pyinfra.api.connectors.util import escape_unix_path
from pyinfra.api.facts import FactBase

from .util.files import parse_ls_output


class File(FactBase):
    # Types must match FLAG_TO_TYPE in .util.files.py
    type = 'file'

    # If the file doesn't exist, return `None` instead of failing
    use_default_on_error = True

    _ls_commands = [
        'ls -ld --time-style=long-iso {0} 2> /dev/null',  # Ubuntu, CentOS
        'ls -ld --full-time {0} 2> /dev/null',  # Newer BusyBox
        'ls -lde {0} 2> /dev/null',  # Older BusyBox
        'ls -ldT {0}',  # BSD, MacOS
    ]

    def command(self, name):
        name = escape_unix_path(name)
        commands = [ls_command.format(name) for ls_command in self._ls_commands]
        return ' || '.join(commands)

    def process(self, output):
        return parse_ls_output(output[0], self.type)


class Link(File):
    type = 'link'


class Directory(File):
    type = 'directory'


class Socket(File):
    type = 'socket'


class Sha1File(FactBase):
    '''
    Returns a SHA1 hash of a file. Works with both sha1sum and sha1.
    '''

    _regexes = [
        r'^([a-zA-Z0-9]{40})\s+%s$',
        r'^SHA1\s+\(%s\)\s+=\s+([a-zA-Z0-9]{40})$',
    ]

    def command(self, name):
        name = escape_unix_path(name)
        self.name = name
        return 'sha1sum {0} 2> /dev/null || shasum {0} 2> /dev/null || sha1 {0}'.format(name)

    def process(self, output):
        for regex in self._regexes:
            regex = regex % self.name
            matches = re.match(regex, output[0])

            if matches:
                return matches.group(1)


class FindInFile(FactBase):
    '''
    Checks for the existence of text in a file using grep. Returns a list of matching
    lines if the file exists, and ``None`` if the file does not.
    '''

    use_default_on_error = True

    def command(self, name, pattern):
        name = escape_unix_path(name)
        pattern = shlex_quote(pattern)

        self.name = name

        return (
            'grep -e {0} {1} 2> /dev/null || '
            '(find {1} -type f > /dev/null && echo "__pyinfra_exists_{1}")'
        ).format(pattern, name).strip()

    def process(self, output):
        # If output is the special string: no matches, so return an empty list;
        # this allows us to differentiate between no matches in an existing file
        # or a file not existing.
        if output and output[0] == '__pyinfra_exists_{0}'.format(self.name):
            return []

        return output


class FindFiles(FactBase):
    '''
    Returns a list of files from a start point, recursively using find.
    '''

    @staticmethod
    def command(name):
        return 'find {0} -type f'.format(escape_unix_path(name))

    @staticmethod
    def process(output):
        return output


class FindLinks(FindFiles):
    '''
    Returns a list of links from a start point, recursively using find.
    '''

    @staticmethod
    def command(name):
        return 'find {0} -type l'.format(escape_unix_path(name))


class FindDirectories(FindFiles):
    '''
    Returns a list of directories from a start point, recursively using find.
    '''

    @staticmethod
    def command(name):
        return 'find {0} -type d'.format(escape_unix_path(name))
