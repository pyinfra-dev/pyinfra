from __future__ import unicode_literals

import re
from datetime import datetime


WIN_LS_REGEX = re.compile((
    # filetype and mode
    r'^([darhsl\-]{6})\s+'
    # Windows date
    r'([0-9]{1,2}\/[0-9]{1,2}\/[0-9]{4})\s+([0-9]{1,2}:[0-9]{1,2}\s[AP][M])\s+'
    # Size (Note: no size on directories)
    r'([0-9]+)?\s+'
    # Size and Filename
    r'([\w\/\.@-]+)'
))

WIN_FLAG_TO_TYPE = {
    'd': 'directory',
    '-': 'file',
}

WIN_FLAG_TO_ATTR = {
    'a': 'archive',
    'r': 'readonly',
    'h': 'hidden',
    's': 'system',
    'l': 'link',
    '-': 'none',
}


def _parse_time(time):
    # Try matching windows format
    try:
        tmp = datetime.strptime(time, '%m/%d/%Y %H:%M %p')
        return tmp
    except ValueError:
        pass


def parse_win_ls_output(output, wanted_type):
    if output:
        matches = re.match(WIN_LS_REGEX, output)
        if matches:
            if output[5] == 'l':
                type = 'link'
            else:
                type = WIN_FLAG_TO_TYPE[output[0]]

            if type != wanted_type:
                return False

            hidden = False
            system = False
            readonly = False
            archive = False
            link = False

            mode_without_first = matches.group(1)[1:]

            for c in mode_without_first:
                tmp = WIN_FLAG_TO_ATTR[c]
                if tmp != 'none':
                    if tmp == 'hidden':
                        hidden = True
                    if tmp == 'readonly':
                        readonly = True
                    if tmp == 'archive':
                        archive = True
                    if tmp == 'system':
                        system = True
                    if tmp == 'link':
                        link = True

            mode = {
                'archive': archive,
                'hidden': hidden,
                'readonly': readonly,
                'system': system,
                'link': link,
            }

            date_and_time = '{} {}'.format(matches.group(2), matches.group(3))

            size = '0'
            if type == 'file':
                size = matches.group(4)

            out = {
                'type': type,
                'mode': mode,
                'mtime': _parse_time(date_and_time),
                'size': size,
                'name': matches.group(5),
                # TODO: You will need to run another powershell command to
                #       get the link target, so bailing on that for now.
            }

            return out
