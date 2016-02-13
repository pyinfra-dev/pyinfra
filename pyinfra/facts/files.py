# pyinfra
# File: pyinfra/facts/server.py
# Desc: filesystem facts

import re
from datetime import datetime

from pyinfra.api.facts import FactBase

LS_REGEX = re.compile(
    r'^[dl\-]([\-rwx]{9})\.?\s+[0-9]+\s+([a-zA-Z]+)\s+([a-zA-Z]+)\s+([0-9]+)\s+([a-zA-Z]{3}\s+[0-9]+\s+[0-9:]{4,5})\s+[a-zA-Z0-9\/\.]+\s*-?>?\s*([a-zA-Z0-9\/\.]*)'
)

SYMBOL_TO_OCTAL_PERMISSIONS = {
    'rwx': '7',
    'rw-': '6',
    'r-x': '5',
    'r--': '4',
    '-wx': '3',
    '-w-': '2',
    '--x': '1'
}


def _parse_mode(mode):
    result = ''
    # owner, group, world
    for group in [mode[0:3], mode[3:6], mode[6:9]]:
        if group in SYMBOL_TO_OCTAL_PERMISSIONS:
            result = '{0}{1}'.format(result, SYMBOL_TO_OCTAL_PERMISSIONS[group])
        else:
            result = '{0}0'.format(result)

    return result


def _parse_time(time):
    # Try matching with the hour/second format, ie within the current year
    try:
        dt = datetime.strptime(time, '%b %d %H:%M')
        return dt.replace(year=datetime.now().year)
    except ValueError:
        pass

    # Otherwise we're in the past, timed to the nearest day
    try:
        return datetime.strptime(time, '%b %d %Y')
    except ValueError:
        pass


def _process_ls_output(output, directory=False, link=False):
    if output:
        matches = re.match(LS_REGEX, output)
        if matches:
            # Ensure we have what we want
            is_directory = output.startswith('d')
            if directory is not is_directory:
                return False

            is_link = output.startswith('l')
            if link is not is_link:
                return False

            out = {
                'mode': _parse_mode(matches.group(1)),
                'user': matches.group(2),
                'group': matches.group(3),
                'size': matches.group(4),
                'mtime': _parse_time(matches.group(5))
            }

            if link:
                out['link_target'] = matches.group(6)

            return out


class File(FactBase):
    def command(self, name):
        return 'ls -ld {0}'.format(name)

    def process(self, output):
        return _process_ls_output(output[0])


class Link(File):
    def process(self, output):
        return _process_ls_output(output[0], link=True)


class Directory(File):
    def process(self, output):
        return _process_ls_output(output[0], directory=True)


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
        for regex in self._regexes:
            matches = re.match(regex, output[0])
            if matches:
                return matches.group(1)


class FindInFile(FactBase):
    '''
    Checks for the existence of text in a file using grep.
    '''

    def command(self, name, pattern):
        return 'grep "{0}" {1}'.format(pattern, name)


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
