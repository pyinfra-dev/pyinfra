# pyinfra
# File: pyinfra/facts/server.py
# Desc: filesystem facts

from __future__ import unicode_literals

import re

from pyinfra.api.facts import FactBase

from .util.files import parse_ls_output


class File(FactBase):
    link = False
    directory = False

    def command(self, name):
        self.name = name
        return 'ls -ld {0}'.format(name)

    def process(self, output):
        return parse_ls_output(
            self.name, output[0],
            link=self.link, directory=self.directory
        )


class Link(File):
    link = True

class Directory(File):
    directory = True


class Sha1File(FactBase):
    '''
    Returns a SHA1 hash of a file. Works with both sha1sum and sha1.
    '''

    _regexes = [
        r'^([a-zA-Z0-9]+)\s+[a-zA-Z0-9_\/\.\-]+$',
        r'^SHA1 \([a-zA-Z0-9_\/\.\-]+\)\s+=\s+([a-zA-Z0-9]+)$'
    ]

    def command(self, name):
        return 'sha1sum {0} || sha1 {0}'.format(name)

    def process(self, output):
        # print 'OUT', output
        for regex in self._regexes:
            matches = re.match(regex, output[0])
            if matches:
                return matches.group(1)


class FindInFile(FactBase):
    '''
    Checks for the existence of text in a file using grep. Returns a list of matching
    lines if the file exists, and ``None`` if the file does not.
    '''

    def command(self, name, pattern):
        self.name = name
        return 'grep "{0}" {1} || find {1}'.format(pattern, name)

    def process(self, output):
        # If output is the filename (ie caught by the || find <filename>), no matches, so
        # return an empty list.
        if output[0] == self.name:
            return []

        return output


class FindFiles(FactBase):
    '''
    Returns a list of files from a start point, recursively using find.
    '''

    def command(self, name):
        return 'find {0} -type f'.format(name)

    def process(self, output):
        return output


class FindLinks(FindFiles):
    '''
    Returns a list of links from a start point, recursively using find.
    '''

    def command(self, name):
        return 'find {0} -type l'.format(name)


class FindDirectories(FindFiles):
    '''
    Returns a list of directories from a start point, recursively using find.
    '''

    def command(self, name):
        return 'find {0} -type d'.format(name)
