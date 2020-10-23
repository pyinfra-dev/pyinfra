from six.moves.urllib.parse import urlparse

from pyinfra.api import FactBase


class GpgFactBase(FactBase):
    abstract = True

    requires_command = 'gpg'

    key_record_type = 'pub'
    subkey_record_type = 'sub'

    def process(self, output):
        # For details on the field values see:
        # https://git.gnupg.org/cgi-bin/gitweb.cgi?p=gnupg.git;a=blob_plain;f=doc/DETAILS
        keys = []

        current_key = None
        current_subkey = None

        for line in output:
            if not line:
                continue

            bits = line.split(':')

            if bits[0] in (self.key_record_type, self.subkey_record_type):
                key_details = {
                    'validity': bits[1],
                    'length': int(bits[2]),
                    'id': bits[4],
                }

                if bits[0] == self.key_record_type:
                    key_details['subkeys'] = []

                    if current_key:
                        if current_subkey:
                            current_key['subkeys'].append(current_subkey)

                        keys.append(current_key)

                    current_key = key_details
                    current_subkey = None
                elif current_key:
                    current_subkey = key_details

            elif current_subkey or current_key:
                target = current_subkey or current_key

                if bits[0] == 'fpr':
                    target['fingerprint'] = bits[9]  # fingerprint = field 10
                elif bits[0] == 'uid':
                    target['uid_hash'] = bits[7]
                    target['uid'] = bits[9]

        if current_key:
            if current_subkey:
                current_key['subkeys'].append(current_subkey)

            keys.append(current_key)

        # Return as a dictionary of keyID -> details
        keys_by_id = {}
        for key in keys:
            if 'subkeys' in key:
                key['subkeys'] = {
                    subkey.pop('id'): subkey
                    for subkey in key['subkeys']
                }
            keys_by_id[key.pop('id')] = key

        return keys_by_id


class GpgKey(GpgFactBase):
    '''
    Returns information on one or more GPG keys found in a file or URL.

    .. code:: python

        {
            'KEY-ID': {
                'length': 4096,
                'uid': 'Oxygem <hello@oxygem.com>'
            },
            ...
        }
    '''

    def command(self, src):
        if urlparse(src).scheme:
            return (
                '(wget -O - {0} || curl -sSLf {0}) | gpg --with-colons'
            ).format(src)

        return 'gpg --with-colons {0}'.format(src)


class GpgKeys(GpgFactBase):
    '''
    Returns information on all public keys in a keychain.

    .. code:: python

        {
            'KEY-ID': {
                'length': 4096,
                'uid': 'Oxygem <hello@oxygem.com>'
            },
            ...
        }
    '''

    def command(self, keyring=None):
        if not keyring:
            return 'gpg --list-keys --with-colons'

        return (
            'gpg --list-keys --with-colons --keyring {0} --no-default-keyring'
        ).format(keyring)


class GpgSecretKeys(GpgFactBase):
    '''
    Returns information on all secret keys in a keychain.

    .. code:: python

        {
            'KEY-ID': {
                'length': 4096,
                'fingerprint': 'ABC',
                'uid': 'Oxygem <hello@oxygem.com>'
            },
            ...
        }
    '''

    key_record_type = 'sec'
    subkey_record_type = 'ssb'

    def command(self, keyring=None):
        if not keyring:
            return 'gpg --list-secret-keys --with-colons'

        return (
            'gpg --list-secret-keys --with-colons --keyring {0} --no-default-keyring'
        ).format(keyring)
