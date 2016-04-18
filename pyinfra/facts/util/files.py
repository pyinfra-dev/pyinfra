# pyinfra
# File: pyinfra/facts/util/files.py
# Desc: file related fact utilities

from __future__ import unicode_literals

import re
from os import path
from datetime import datetime


LS_REGEX = re.compile(
    r'^[dl\-]([\-rwx]{9})\.?\s+[0-9]+\s+([a-zA-Z]+)\s+([a-zA-Z]+)\s+([0-9]+)\s+([a-zA-Z]{3}\s+[0-9]+\s+[0-9:]{4,5})\s+[a-zA-Z0-9\/\.\-]+\s?-?>?\s?([a-zA-Z0-9\/\.\-]*)'
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
    '''
    Converts ls mode output (rwxrwxrwx) -> integer (755).
    '''

    result = ''
    # owner, group, world
    for group in [mode[0:3], mode[3:6], mode[6:9]]:
        if group in SYMBOL_TO_OCTAL_PERMISSIONS:
            result = '{0}{1}'.format(result, SYMBOL_TO_OCTAL_PERMISSIONS[group])
        else:
            result = '{0}0'.format(result)

    # Return as an integer
    return int(result)


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


def parse_ls_output(filename, output, directory=False, link=False):
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
                target = matches.group(6)

                # If not an absolute path, combine with the source to get one
                if not path.isabs(target):
                    target_filename = path.basename(target)
                    target_dirname = path.dirname(target)
                    source_dirname = path.dirname(filename)

                    target_dirname = path.normpath(
                        path.join(source_dirname, target_dirname)
                    )
                    target = path.join(target_dirname, target_filename)

                out['link_target'] = target

            return out
