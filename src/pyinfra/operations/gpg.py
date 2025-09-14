"""
Manage GPG keys and keyrings.
"""

from __future__ import annotations

from urllib.parse import urlparse

from pyinfra import host
from pyinfra.api import OperationError, operation
from pyinfra.facts.gpg import GpgKey

from . import files
from pathlib import Path


@operation()
def key(
    src: str | None = None,
    dest: str | None = None,
    keyserver: str | None = None,
    keyid: str | list[str] | None = None,
    dearmor: bool = True,
    mode: str = "0644",
    present: bool = True,
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
                When False: if dest is provided, removes from specific keyring;
                           if dest is None, removes from all APT keyrings;
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
            name="Remove key from all APT keyrings",
            keyid="0xCOMPROMISED123",
            present=False,
            # dest=None means search in all keyrings
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
        # For removal, either dest or keyid must be provided
        if not dest and not keyid:
            raise OperationError("For removal, either `dest` or `keyid` must be provided")

    # For removal, handle different scenarios
    if present is False:
        if not dest and keyid:
            # Remove key(s) from all APT keyrings
            if isinstance(keyid, str):
                keyid = [keyid]
            
            # Define all APT keyring locations
            keyring_patterns = [
                "/etc/apt/trusted.gpg.d/*.gpg",
                "/etc/apt/keyrings/*.gpg", 
                "/usr/share/keyrings/*.gpg"
            ]
            
            for pattern in keyring_patterns:
                for kid in keyid:
                    # Remove key from all matching keyrings
                    yield f'for keyring in {pattern}; do [ -e "$keyring" ] && gpg --batch --no-default-keyring --keyring "$keyring" --delete-keys {kid} 2>/dev/null || true; done'
                
                # Clean up empty keyrings
                yield f'for keyring in {pattern}; do [ -e "$keyring" ] && ! gpg --batch --no-default-keyring --keyring "$keyring" --list-keys 2>/dev/null | grep -q "pub" && rm -f "$keyring" || true; done'
            
            return
            
        elif dest and keyid:
            # Remove specific key(s) by ID from specific keyring
            if isinstance(keyid, str):
                keyid = [keyid]
            
            for kid in keyid:
                # Remove the specific key from the keyring
                yield f'gpg --batch --no-default-keyring --keyring "{dest}" --delete-keys {kid} 2>/dev/null || true'
            
            # If keyring becomes empty, remove the file
            yield f'if ! gpg --batch --no-default-keyring --keyring "{dest}" --list-keys 2>/dev/null | grep -q "pub"; then rm -f "{dest}"; fi'
            return
            
        elif dest and not keyid:
            # Remove entire keyring file
            yield from files.file._inner(
                path=dest,
                present=False,
            )
            return

    # For installation, validate required parameters
    if not src and not keyserver:
        raise OperationError("Either `src` or `keyserver` must be provided for installation")

    if keyserver and not keyid:
        raise OperationError("`keyid` must be provided with `keyserver`")

    if keyid and not keyserver and not src:
        raise OperationError("When using `keyid` for installation, either `keyserver` or `src` must be provided")

    # For installation (present=True), ensure destination directory exists
    dest_dir = str(Path(dest).parent)
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
        if isinstance(keyid, str):
            keyid = [keyid]

        joined = " ".join(keyid)

        # Create temporary GPG home directory using pyinfra
        temp_dir = f"/tmp/pyinfra-gpg-{host.get_temp_filename('')[-8:]}"

        yield from files.directory._inner(
            path=temp_dir,
            mode="0700",  # GPG directories should be more restrictive
            present=True,
        )

        # Export GNUPGHOME and fetch keys
        yield f'export GNUPGHOME="{temp_dir}" && gpg --batch --keyserver "{keyserver}" --recv-keys {joined}'

        # Export keys to destination
        if dearmor:
            yield f'export GNUPGHOME="{temp_dir}" && gpg --batch --export {joined} | gpg --batch --dearmor -o "{dest}"'
        else:
            yield f'export GNUPGHOME="{temp_dir}" && gpg --batch --export {joined} > "{dest}"'

        # Clean up temporary directory using pyinfra
        yield from files.directory._inner(
            path=temp_dir,
            present=False,
        )

        # Set proper permissions using pyinfra
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
    dest_dir = dest.rsplit("/", 1)[0]
    yield from files.directory._inner(
        path=dest_dir,
        mode="0755",
        present=True,
    )

    yield f'gpg --batch --dearmor -o "{dest}" "{src}"'

    # Set proper permissions using pyinfra
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
        # Note: Could be enhanced using GpgKey fact for better detection
        yield f'if grep -q "BEGIN PGP PUBLIC KEY BLOCK" "{src_file}"; then gpg --batch --dearmor -o "{dest_path}" "{src_file}"; else cp "{src_file}" "{dest_path}"; fi'
    else:
        # Simple copy for binary keys or when dearmoring is disabled
        yield f'cp "{src_file}" "{dest_path}"'

    # Set proper permissions using pyinfra
    yield from files.file._inner(
        path=dest_path,
        mode=mode,
        present=True,
    )
