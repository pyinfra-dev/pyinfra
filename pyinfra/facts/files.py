# pyinfra
# File: pyinfra/facts/server.py
# Desc: filesystem facts

import re

from pyinfra.api.facts import FactBase

LS_REGEX = re.compile(
    r'^[a-z-]?([-rwx]{9})\.?\s+[0-9]+\s+([a-zA-Z]+)\s+([a-zA-Z]+)\s+([0-9]+)\s+[a-zA-Z]{3}\s+[0-9]+\s+[0-9]{2}:[0-9]{2}\s+[a-zA-Z0-9\.]+$'
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

def _parse_ls_output(output, directory=False):
    if output:
        matches = re.match(LS_REGEX, output)
        if matches:
            # Ensure we have what we want
            is_directory = output.startswith('d')
            if directory != is_directory:
                return False # stands for the wrong type

            directory = _ls_matches_to_dict(matches)
            return directory


def _ls_matches_to_dict(matches):
    '''Parse mode into octal format (which is what we compare to deploy scripts).'''
    def parse_mode(mode):
        result = ''
        # owner, group, world
        for group in [mode[0:3], mode[3:6], mode[6:9]]:
            if group in SYMBOL_TO_OCTAL_PERMISSIONS:
                result = '{0}{1}'.format(result, SYMBOL_TO_OCTAL_PERMISSIONS[group])
            else:
                result = '{0}0'.format(result)

        return result

    return {
        'mode': parse_mode(matches.group(1)),
        'user': matches.group(2),
        'group': matches.group(3),
        'size': matches.group(4)
    }


class File(FactBase):
    def command(self, name):
        return 'ls -ldp {0}'.format(name)

    def process(self, output):
        return _parse_ls_output(output[0])


class Directory(File):
    def process(self, output):
        return _parse_ls_output(output[0], directory=True)


class Sha1File(FactBase):
    '''Returns a SHA1 hash of a file. Works with both sha1sum and sha1.'''
    regexes = [
        r'^([a-zA-Z0-9]+)\s+[a-zA-Z0-9_\/\.\-]+$',
        r'^SHA1 \([a-zA-Z0-9_\/\.\-]+\)\s+=\s+([a-zA-Z0-9]+)$'
    ]

    def command(self, name):
        return 'sha1sum {0} || sha1 {0}'.format(name)

    def process(self, output):
        for regex in self.regexes:
            matches = re.match(regex, output[0])
            if matches:
                return matches.group(1)
