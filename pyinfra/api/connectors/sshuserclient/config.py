'''
This file as originally part of the "sshuserclient" pypi package. The GitHub
source has now vanished (https://github.com/tobald/sshuserclient).
'''

import glob
import os
import re

from paramiko import SSHConfig as ParamikoSSHConfig


class SSHConfig(ParamikoSSHConfig):
    '''
    an SSHConfig that supports includes directives
    https://github.com/paramiko/paramiko/pull/1194
    '''

    SETTINGS_REGEX = re.compile(r'(\w+)(?:\s*=\s*|\s+)(.+)')

    def parse(self, file_obj, parsed_files=None):
        '''
        Read an OpenSSH config from the given file object.

        :param file_obj: a file-like object to read the config file from
        '''
        host = {'host': ['*'], 'config': {}}
        for line in file_obj:
            # Strip any leading or trailing whitespace from the line.
            # Refer to https://github.com/paramiko/paramiko/issues/499
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            match = re.match(self.SETTINGS_REGEX, line)
            if not match:
                raise Exception('Unparsable line {}'.format(line))
            key = match.group(1).lower()
            value = match.group(2)

            if key == 'host':
                self._config.append(host)
                host = {
                    'host': self._get_hosts(value),
                    'config': {},
                }
            elif key == 'proxycommand' and value.lower() == 'none':
                # Store 'none' as None; prior to 3.x, it will get stripped out
                # at the end (for compatibility with issue #415). After 3.x, it
                # will simply not get stripped, leaving a nice explicit marker.
                host['config'][key] = None
            elif key == 'include':
                # support for Include directive in ssh_config
                path = value
                # the path can be relative to its parent configuration file
                if os.path.isabs(path) is False and path[0] != '~':
                    folder = os.path.dirname(file_obj.name)
                    path = os.path.join(folder, path)

                # expand the user home path
                path = os.path.expanduser(path)
                if parsed_files is None:
                    parsed_files = []

                # parse every included file
                for filename in glob.iglob(path):
                    if os.path.isfile(filename):
                        if filename in parsed_files:
                            raise Exception(
                                'Include loop detected in ssh config file: %s' % filename,
                            )
                        with open(filename) as fd:
                            parsed_files.append(filename)
                            self.parse(fd, parsed_files)

            else:
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]

                # identityfile, localforward, remoteforward keys are special
                # cases, since they are allowed to be specified multiple times
                # and they should be tried in order of specification.
                if key in ['identityfile', 'localforward', 'remoteforward']:
                    if key in host['config']:
                        host['config'][key].append(value)
                    else:
                        host['config'][key] = [value]
                elif key not in host['config']:
                    host['config'][key] = value
        self._config.append(host)
