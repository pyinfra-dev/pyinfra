'''
This file as originally part of the "sshuserclient" pypi package. The GitHub
source has now vanished (https://github.com/tobald/sshuserclient).
'''

import glob
import re

from os import path

from paramiko import SSHConfig as ParamikoSSHConfig
from six import StringIO

SETTINGS_REGEX = re.compile(r'(\w+)(?:\s*=\s*|\s+)(.+)')


def _expand_include_statements(file_obj, parsed_files=None):
    parsed_lines = []

    for line in file_obj:
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        match = re.match(SETTINGS_REGEX, line)
        if not match:
            parsed_lines.append(line)
            continue

        key = match.group(1).lower()
        value = match.group(2)

        if key != 'include':
            parsed_lines.append(line)
            continue

        if parsed_files is None:
            parsed_files = []

        # The path can be relative to its parent configuration file
        if path.isabs(value) is False and value[0] != '~':
            folder = path.dirname(file_obj.name)
            value = path.join(folder, value)

        value = path.expanduser(value)

        for filename in glob.iglob(value):
            if path.isfile(filename):
                if filename in parsed_files:
                    raise Exception(
                        'Include loop detected in ssh config file: %s' % filename,
                    )
                with open(filename) as fd:
                    parsed_files.append(filename)
                    parsed_lines.extend(_expand_include_statements(fd, parsed_files))

    return parsed_lines
    output = StringIO('\n'.join(parsed_lines))
    output.name = file_obj.name
    return output


class SSHConfig(ParamikoSSHConfig):
    '''
    an SSHConfig that supports includes directives
    https://github.com/paramiko/paramiko/pull/1194
    '''

    def parse(self, file_obj):
        file_obj = _expand_include_statements(file_obj)
        return super(SSHConfig, self).parse(file_obj)
