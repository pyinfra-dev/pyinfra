from __future__ import annotations

from urllib.parse import urlparse

from typing_extensions import override

from pyinfra.api import FactBase


class GpgFactBase(FactBase):
    abstract = True

    @override
    def requires_command(self, *args, **kwargs) -> str:
        return "gpg"

    key_record_type = "pub"
    subkey_record_type = "sub"

    @override
    def process(self, output):
        # For details on the field values see:
        # https://git.gnupg.org/cgi-bin/gitweb.cgi?p=gnupg.git;a=blob_plain;f=doc/DETAILS
        keys = []

        current_key = None
        current_subkey = None

        for line in output:
            if not line:
                continue

            bits = line.split(":")

            if bits[0] in (self.key_record_type, self.subkey_record_type):
                key_details = {
                    "validity": bits[1],
                    "length": int(bits[2]),
                    "id": bits[4],
                }

                if bits[0] == self.key_record_type:
                    key_details["subkeys"] = []

                    if current_key:
                        if current_subkey:
                            current_key["subkeys"].append(current_subkey)

                        keys.append(current_key)

                    current_key = key_details
                    current_subkey = None
                elif current_key:
                    current_subkey = key_details

            elif current_subkey or current_key:
                target = current_subkey or current_key
                assert target is not None
                if bits[0] == "fpr":
                    target["fingerprint"] = bits[9]  # fingerprint = field 10
                elif bits[0] == "uid":
                    target["uid_hash"] = bits[7]
                    target["uid"] = bits[9]

        if current_key:
            if current_subkey:
                current_key["subkeys"].append(current_subkey)

            keys.append(current_key)

        # Return as a dictionary of keyID -> details
        keys_by_id = {}
        for key in keys:
            if "subkeys" in key:
                key["subkeys"] = {subkey.pop("id"): subkey for subkey in key["subkeys"]}
            keys_by_id[key.pop("id")] = key

        return keys_by_id


class GpgKey(GpgFactBase):
    """
    Returns information on one or more GPG keys found in a file or URL.

    .. code:: python

        {
            "KEY-ID": {
                "length": 4096,
                "uid": "Oxygem <hello@oxygem.com>"
            },
        }
    """

    @override
    def command(self, src):
        if urlparse(src).scheme:
            return ("(wget -O - {0} || curl -sSLf {0}) | gpg --with-colons").format(src)

        return "gpg --with-colons {0}".format(src)


class GpgKeys(GpgFactBase):
    """
    Returns information on all public keys in a keychain.

    .. code:: python

        {
            "KEY-ID": {
                "length": 4096,
                "uid": "Oxygem <hello@oxygem.com>"
            },
        }
    """

    @override
    def command(self, keyring=None):
        if not keyring:
            return "gpg --list-keys --with-colons"

        return ("gpg --list-keys --with-colons --keyring {0} --no-default-keyring").format(keyring)


class GpgSecretKeys(GpgFactBase):
    """
    Returns information on all secret keys in a keychain.

    .. code:: python

        {
            "KEY-ID": {
                "length": 4096,
                "fingerprint": "ABC",
                "uid": "Oxygem <hello@oxygem.com>"
            },
        }
    """

    key_record_type = "sec"
    subkey_record_type = "ssb"

    @override
    def command(self, keyring=None):
        if not keyring:
            return "gpg --list-secret-keys --with-colons"

        return ("gpg --list-secret-keys --with-colons --keyring {0} --no-default-keyring").format(
            keyring,
        )


class GpgKeyrings(GpgFactBase):
    """
    Returns information on all GPG keyrings found in specified directories.

    .. code:: python

        {
            "/etc/apt/keyrings/docker.gpg": {
                "format": "gpg",
                "keys": {...}  # Same format as GpgKeys fact
            }
        }
    """

    @override
    def command(self, directories):
        if isinstance(directories, str):
            directories = [directories]

        search_locations = " ".join(f'"{d}"' for d in directories)

        # Two separate find+exec calls to avoid bash-specific syntax:
        # - binary keyrings (.gpg, .kbx) use --keyring / --no-default-keyring
        # - armored keyrings (.asc) are passed directly to gpg
        return (
            f"find {search_locations} -type f \\( -name '*.gpg' -o -name '*.kbx' \\) 2>/dev/null"
            f' -exec sh -c \'echo "KEYRING:$1";'
            f' gpg --list-keys --with-colons --keyring "$1" --no-default-keyring 2>/dev/null || true\' _ {{}} \\; ;'
            f" find {search_locations} -type f -name '*.asc' 2>/dev/null"
            f' -exec sh -c \'echo "KEYRING:$1"; gpg --with-colons "$1" 2>/dev/null || true\' _ {{}} \\;'
        )

    @override
    def process(self, output):
        keyrings = {}
        current_keyring = None
        current_output: list[str] = []

        for line in output:
            line = line.strip()
            if not line:
                continue

            if line.startswith("KEYRING:"):
                # Process previous keyring if exists
                if current_keyring and current_output:
                    keyring_format = current_keyring.split(".")[-1].lower()
                    keys = super().process(current_output)
                    keyrings[current_keyring] = {"format": keyring_format, "keys": keys}

                # Start new keyring
                current_keyring = line[8:]  # Remove "KEYRING:" prefix
                current_output = []
            else:
                # Accumulate GPG output for current keyring
                current_output.append(line)

        # Process final keyring
        if current_keyring and current_output:
            keyring_format = current_keyring.split(".")[-1].lower()
            keys = super().process(current_output)
            keyrings[current_keyring] = {"format": keyring_format, "keys": keys}

        return keyrings
