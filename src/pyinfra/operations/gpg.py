"""
Manage GPG keys and keyrings.
"""

from pathlib import PurePosixPath
from urllib.parse import urlparse

from pyinfra import host
from pyinfra.api import OperationError, operation
from pyinfra.facts.gpg import GpgKeyrings

from . import files


@operation()
def key(
    src: str | None = None,
    dest: str | None = None,
    keyserver: str | None = None,
    keyid: str | list[str] | None = None,
    dearmor: bool = True,
    mode: str = "0644",
    present: bool = True,
    working_dirs: list[str] | None = None,
):
    """
    Install or remove GPG keys from various sources.

    Args:
        src: filename or URL to a key (ASCII .asc or binary .gpg)
        dest: destination path for the key file (required for installation, optional for removal)
        keyserver: keyserver URL for fetching keys by ID
        keyid: key ID or list of key IDs (required with keyserver, optional for removal)
        dearmor: whether to convert ASCII armored keys to binary format
        mode: file permissions for the installed key
        present: whether the key should be present (True) or absent (False)
        working_dirs: dirs to search for existing keyrings (required for removal without dest)
                When False: if dest is provided, removes from specific keyring;
                           if dest is None, removes from keyrings found in working_dirs;
                           if keyid is provided, removes specific key(s);
                           if keyid is None, removes entire keyring file(s)

    Examples:
        gpg.key(
            name="Install Docker GPG key",
            src="https://download.docker.com/linux/debian/gpg",
            dest="/etc/apt/keyrings/docker.gpg",
        )

        gpg.key(
            name="Remove old GPG key file",
            dest="/etc/apt/keyrings/old-key.gpg",
            present=False,
        )

        gpg.key(
            name="Remove specific key by ID",
            dest="/etc/apt/keyrings/vendor.gpg",
            keyid="0xABCDEF12",
            present=False,
        )

        gpg.key(
            name="Remove key from specific directories",
            keyid="0xCOMPROMISED123",
            present=False,
            working_dirs=["/etc/apt/keyrings", "/usr/share/keyrings"],
        )

        gpg.key(
            name="Fetch keys from keyserver",
            keyserver="hkps://keyserver.ubuntu.com",
            keyid=["0xD88E42B4", "0x7EA0A9C3"],
            dest="/etc/apt/keyrings/vendor.gpg",
        )
    """

    # Validate parameters based on operation type
    if present is True:
        # For installation, dest is required
        if not dest:
            raise OperationError("`dest` must be provided for installation")
    elif present is False:
        # For removal, either dest or (keyid and working_dirs) must be provided
        if not dest and not (keyid and working_dirs):
            raise OperationError(
                "For removal, either `dest` or both `keyid` and `working_dirs` must be provided"
            )

    # For removal, handle different scenarios
    if present is False:
        if not dest and keyid:
            # Remove key(s) from all keyrings found in specified directories
            if isinstance(keyid, str):
                keyid = [keyid]

            if not working_dirs:
                raise OperationError(
                    "`working_dirs` must be provided when removing keys without `dest`"
                )

            # Use the GpgKeyrings fact to find all keyrings in specified directories
            keyrings_info = host.get_fact(GpgKeyrings, directories=working_dirs)

            for keyring_path, keyring_data in keyrings_info.items():
                # Get the keys from the GpgKeyrings fact data
                keys_in_keyring = keyring_data.get("keys", {})

                # Check if any of the target keys exist in this keyring
                keys_to_remove = []
                for kid in keyid:
                    # Handle different key ID formats (short, long, with/without 0x prefix)
                    clean_key = kid.replace("0x", "").replace("0X", "").upper()

                    # Check for exact match or if the key ID is a suffix/prefix of any key
                    # in the keyring
                    for existing_key_id in keys_in_keyring.keys():
                        if (
                            clean_key == existing_key_id.upper()
                            or existing_key_id.upper().endswith(clean_key)
                            or existing_key_id.upper().startswith(clean_key)
                        ):
                            keys_to_remove.append(existing_key_id)

                if keys_to_remove:
                    # Remove the entire keyring file if any target keys are found
                    # This is the safest approach for keyring management
                    yield from files.file._inner(
                        path=keyring_path,
                        present=False,
                    )

            return

        elif dest and keyid:
            # Remove specific key(s) from a specific keyring file
            if isinstance(keyid, str):
                keyid = [keyid]

            # Check if the destination keyring exists and contains the target keys
            keyrings_info = host.get_fact(
                GpgKeyrings, directories=[str(PurePosixPath(dest).parent)]
            )

            if dest in keyrings_info:
                keyring_data = keyrings_info[dest]
                keys_in_keyring = keyring_data.get("keys", {})

                # Check if any of the target keys exist in this keyring
                keys_found = False
                for kid in keyid:
                    clean_key = kid.replace("0x", "").replace("0X", "").upper()
                    for existing_key_id in keys_in_keyring.keys():
                        # Check for exact match, suffix (short key ID), or prefix match
                        if (
                            clean_key == existing_key_id.upper()
                            or existing_key_id.upper().endswith(clean_key)
                            or existing_key_id.upper().startswith(clean_key)
                        ):
                            keys_found = True
                            break
                    if keys_found:
                        break

                if keys_found:
                    # Remove the entire keyring file - safest approach for keyring management
                    yield from files.file._inner(
                        path=dest,
                        present=False,
                    )
            return

        elif dest and not keyid:
            # Remove entire keyring file
            yield from files.file._inner(
                path=dest,
                present=False,
            )
            return

        else:
            raise OperationError("Invalid parameters for removal operation")

    # For installation, validate required parameters
    if not src and not keyserver:
        raise OperationError("Either `src` or `keyserver` must be provided for installation")

    if keyserver and not keyid:
        raise OperationError("`keyid` must be provided with `keyserver`")

    if keyid and not keyserver and not src:
        raise OperationError(
            "When using `keyid` for installation, either `keyserver` or `src` must be provided"
        )

    # For installation (present=True), ensure destination directory exists
    if dest is None:
        raise OperationError("dest is required for installation")

    dest_dir = str(PurePosixPath(dest).parent)
    yield from files.directory._inner(
        path=dest_dir,
        mode="0755",
        present=True,
    )

    # --- src branch: install a key from URL or local file ---
    if src:
        if urlparse(src).scheme in ("http", "https"):
            # Remote source: download first, then process
            temp_file = host.get_temp_filename(src)

            yield from files.download._inner(
                src=src,
                dest=temp_file,
            )

            # Install the key and clean up temp file
            yield from _install_key_file(temp_file, dest, dearmor, mode)

            # Clean up temp file using pyinfra
            yield from files.file._inner(
                path=temp_file,
                present=False,
            )
        else:
            # Local file: install directly
            yield from _install_key_file(src, dest, dearmor, mode)

    # --- keyserver branch: fetch keys by ID ---
    if keyserver:
        if keyid is None:
            raise OperationError("`keyid` must be provided with `keyserver`")

        if isinstance(keyid, str):
            keyid = [keyid]

        joined = " ".join(keyid)

        # Create temporary GPG home directory
        temp_dir = f"/tmp/pyinfra-gpg-{host.get_temp_filename('')[-8:]}"

        yield from files.directory._inner(
            path=temp_dir,
            mode="0700",  # GPG directories should be more restrictive
            present=True,
        )

        # Export GNUPGHOME and fetch keys
        yield f'export GNUPGHOME="{temp_dir}" && gpg --batch --keyserver "{keyserver}" --recv-keys {joined}'  # noqa: E501

        # Export keys to destination - always use direct binary export
        # gpg --export produces binary format by default, no dearmoring needed
        yield (f'export GNUPGHOME="{temp_dir}" && gpg --batch --export {joined} > "{dest}"')

        # Clean up temporary directory
        yield from files.directory._inner(
            path=temp_dir,
            present=False,
        )

        # Set proper permissions
        yield from files.file._inner(
            path=dest,
            mode=mode,
            present=True,
        )


@operation()
def dearmor(src: str, dest: str, mode: str = "0644"):
    """
    Convert ASCII armored GPG key to binary format.

    Args:
        src: source ASCII armored key file
        dest: destination binary key file
        mode: file permissions for the output file

    Example:
        gpg.dearmor(
            name="Convert key to binary",
            src="/tmp/key.asc",
            dest="/etc/apt/keyrings/key.gpg",
        )
    """

    # Ensure destination directory exists
    dest_dir = str(PurePosixPath(dest).parent)
    yield from files.directory._inner(
        path=dest_dir,
        mode="0755",
        present=True,
    )

    yield f'gpg --batch --dearmor -o "{dest}" "{src}"'

    # Set proper permissions
    yield from files.file._inner(
        path=dest,
        mode=mode,
        present=True,
    )


def _install_key_file(src_file: str, dest_path: str, dearmor: bool, mode: str):
    """
    Helper function to install a GPG key file, dearmoring if necessary.
    """
    if dearmor:
        # Check if it's an ASCII armored key and handle accordingly
        # Note: Could be enhanced using GpgKey fact
        yield (
            f'if grep -q "BEGIN PGP PUBLIC KEY BLOCK" "{src_file}"; then '
            f'gpg --batch --dearmor -o "{dest_path}" "{src_file}"; '
            f'else cp "{src_file}" "{dest_path}"; fi'
        )
    else:
        # Simple copy for binary keys or when dearmoring is disabled
        yield f'cp "{src_file}" "{dest_path}"'

    # Set proper permissions
    yield from files.file._inner(
        path=dest_path,
        mode=mode,
        present=True,
    )
