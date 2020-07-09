from __future__ import unicode_literals

import re

from dateutil.parser import parse as parse_date

LS_REGEX = re.compile((
    # Type flag
    r'^[bcdlsp\-]'
    # Permissions/ACL
    r'([\-rwxsS]{9})[\.\+]?\s+'
    # Links (unused)
    r'[0-9]+\s+'
    # User & group
    r'([\w-]+)\s+([\w-]+)\s+'
    # Size
    r'([0-9]+)\s+'
    # Date start options
    r'((?:'
    # BSD format
    r'[a-zA-Z]{3}\s+[0-9]{1,2}\s+[0-9:]{8}\s+[0-9]{4}'
    # Or Linux format (--time-style=long-iso)
    r'|[0-9]{4}\-[0-9]{2}\-[0-9]{2}\s+[0-9:]{5}'
    # Or Linux format (BusyBox --full-time)
    r'|[0-9]{4}\-[0-9]{2}\-[0-9]{2}\s+[0-9:]{8}\s+[+-][0-9]{4}'
    # Or Linux format (BusyBox -e)
    r'|[A-Za-z]{3}\s[A-Za-z]{3}\s+[0-9]+\s[0-9:]{8}\s+[0-9]{4}'
    # Date end
    r'))\s+'
    # Filename
    r'[\w\/\.@-]+'
    # Optional link target
    r'\s?-?>?\s?([\w\/\.@-]*)'
))

FLAG_TO_TYPE = {
    'b': 'block',
    'c': 'character',
    'd': 'directory',
    'l': 'link',
    's': 'socket',
    'p': 'fifo',
    '-': 'file',
}

SYMBOL_TO_OCTAL_PERMISSIONS = {
    'rwx': '7',
    'rw-': '6',
    'r-x': '5',
    'r--': '4',
    '-wx': '3',
    '-w-': '2',
    '--x': '1',
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


def parse_ls_output(output, wanted_type):
    if output:
        matches = re.match(LS_REGEX, output)
        if matches:
            type = FLAG_TO_TYPE[output[0]]

            if type != wanted_type:
                return False

            try:
                # ignoretz because times are always relative to the server
                mtime = parse_date(matches.group(5), ignoretz=True)
            except ValueError:
                mtime = None

            out = {
                'mode': _parse_mode(matches.group(1)),
                'user': matches.group(2),
                'group': matches.group(3),
                'size': matches.group(4),
                'mtime': mtime,
            }

            if type == 'link':
                out['link_target'] = matches.group(6)

            return out
