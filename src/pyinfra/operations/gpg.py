"""
Manage GPG keys and keyrings.
"""

from __future__ import annotations

from urllib.parse import urlparse

from pyinfra import host
from pyinfra.api import OperationError, operation
from pyinfra.facts.gpg import GpgKey

from . import files


@operation()
def key(
    src: str | None = None,
    dest: str | None = None,
    keyserver: str | None = None,
    keyid: str | list[str] | None = None,
    dearmor: bool = True,
    mode: str = "0644",
):
    """
    Install GPG keys from various sources.

    Args:
        src: filename or URL to a key (ASCII .asc or binary .gpg)
        dest: destination path for the key file (required)
        keyserver: keyserver URL for fetching keys by ID
        keyid: key ID or list of key IDs (required with keyserver)
        dearmor: whether to convert ASCII armored keys to binary format
        mode: file permissions for the installed key

    Examples:
        gpg.key(
            name="Install Docker GPG key",
            src="https://download.docker.com/linux/debian/gpg",
            dest="/etc/apt/keyrings/docker.gpg",
        )

        gpg.key(
            name="Fetch keys from keyserver",
            keyserver="hkps://keyserver.ubuntu.com",
            keyid=["0xD88E42B4", "0x7EA0A9C3"],
            dest="/etc/apt/keyrings/vendor.gpg",
        )
    """

    if not src and not keyserver:
        raise OperationError("Either `src` or `keyserver` must be provided")

    if keyserver and not keyid:
        raise OperationError("`keyid` must be provided with `keyserver`")

    if not dest:
        raise OperationError("`dest` must be provided")

    # Ensure destination directory exists
    dest_dir = dest.rsplit("/", 1)[0]
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
        yield f'if grep -q "BEGIN PGP PUBLIC KEY BLOCK" "{src_file}"; then gpg --batch --dearmor -o "{dest_path}" "{src_file}"; else cp "{src_file}" "{dest_path}"; fi'
    else:
        yield f'cp "{src_file}" "{dest_path}"'

    # Set proper permissions using pyinfra
    yield from files.file._inner(
        path=dest_path,
        mode=mode,
        present=True,
    )
