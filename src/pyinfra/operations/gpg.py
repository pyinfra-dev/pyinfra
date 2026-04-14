"""
Manage GPG keys and keyrings.
"""

from pathlib import PurePosixPath
from urllib.parse import urlparse

from pyinfra import host
from pyinfra.api import OperationError, operation
from pyinfra.facts.gpg import GpgKeyrings
from pyinfra.facts import files as file_facts

from . import files


def _install_key_from_src(src: str, dest: str, dearmor: bool, mode: str):
    """Install a GPG key from a file or URL."""
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


def _install_key_from_keyserver(keyserver: str, keyid: str | list[str], dest: str, mode: str):
    """Install GPG keys from a keyserver."""
    if isinstance(keyid, str):
        keyid = [keyid]

    joined = " ".join(keyid)

    # Create temporary GPG home directory
    temp_dir = host.get_temp_filename(f"gpg-keyserver-{joined}")

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


def _matches_keyid(existing_key_id: str, clean_key: str) -> bool:
    """Check if existing_key_id matches a cleaned (no 0x prefix, uppercase) key ID.

    Supports all common GPG key ID forms:
    - Short 8-char ID:   clean_key is a suffix of existing_key_id  (existing.endswith)
    - Long 16-char ID:   exact match
    - Full fingerprint:  clean_key ends with existing_key_id        (clean.endswith)
    """
    existing_upper = existing_key_id.upper()
    return (
        clean_key == existing_upper
        or existing_upper.endswith(clean_key)
        or existing_upper.startswith(clean_key)
        or clean_key.endswith(existing_upper)  # full fingerprint → short key ID
    )


def _remove_key_from_keyrings(keyid: str | list[str], working_dirs: list[str]):
    """Remove specific keys from all keyrings in specified directories."""
    if isinstance(keyid, str):
        keyid = [keyid]

    # Use the GpgKeyrings fact to find all keyrings in specified directories
    keyrings_info = host.get_fact(GpgKeyrings, directories=working_dirs)

    for keyring_path, keyring_data in keyrings_info.items():
        keyring_format = keyring_data.get("format", "gpg")
        keys_in_keyring = keyring_data.get("keys", {})

        # Collect fingerprints of matching keys to remove
        fingerprints_to_remove = []
        for kid in keyid:
            clean_key = kid.replace("0x", "").replace("0X", "").upper()
            for existing_key_id, key_info in keys_in_keyring.items():
                if _matches_keyid(existing_key_id, clean_key):
                    fingerprint = key_info.get("fingerprint", existing_key_id)
                    if fingerprint not in fingerprints_to_remove:
                        fingerprints_to_remove.append(fingerprint)

        if not fingerprints_to_remove:
            continue

        if keyring_format == "asc":
            # .asc (armored) files cannot be edited in-place.
            # If only some keys match, we cannot selectively remove them.
            if len(fingerprints_to_remove) < len(keys_in_keyring):
                raise OperationError(
                    f"Cannot remove individual keys from armored keyring {keyring_path!r}: "
                    "the file contains other keys and cannot be edited in-place. "
                    "Remove the file explicitly with present=False and no keyid."
                )
            yield from files.file._inner(path=keyring_path, present=False)
        else:
            # .gpg / .kbx: delete keys individually, then remove file if now empty
            fingerprints_joined = " ".join(fingerprints_to_remove)
            yield (
                f'gpg --batch --yes --no-default-keyring --keyring "{keyring_path}"'
                f" --delete-keys {fingerprints_joined}"
            )
            yield (
                f'gpg --batch --no-default-keyring --keyring "{keyring_path}"'
                f' --list-keys 2>/dev/null | grep -q "^pub" || rm -f "{keyring_path}"'
            )


def _remove_key_from_keyring(keyid: str | list[str], dest: str):
    """Remove specific keys from a specific keyring file."""
    if isinstance(keyid, str):
        keyid = [keyid]

    # Check if the destination keyring exists and contains the target keys
    keyrings_info = host.get_fact(GpgKeyrings, directories=[str(PurePosixPath(dest).parent)])

    if dest not in keyrings_info:
        return

    keyring_data = keyrings_info[dest]
    keyring_format = keyring_data.get("format", "gpg")
    keys_in_keyring = keyring_data.get("keys", {})

    # Collect fingerprints of matching keys to remove
    fingerprints_to_remove = []
    for kid in keyid:
        clean_key = kid.replace("0x", "").replace("0X", "").upper()
        for existing_key_id, key_info in keys_in_keyring.items():
            if _matches_keyid(existing_key_id, clean_key):
                fingerprint = key_info.get("fingerprint", existing_key_id)
                if fingerprint not in fingerprints_to_remove:
                    fingerprints_to_remove.append(fingerprint)

    if not fingerprints_to_remove:
        return

    if keyring_format == "asc":
        # .asc (armored) files cannot be edited in-place.
        # If only some keys match, we cannot selectively remove them.
        if len(fingerprints_to_remove) < len(keys_in_keyring):
            raise OperationError(
                f"Cannot remove individual keys from armored keyring {dest!r}: "
                "the file contains other keys and cannot be edited in-place. "
                "Remove the file explicitly with present=False and no keyid."
            )
        yield from files.file._inner(path=dest, present=False)
    else:
        # .gpg / .kbx: delete keys individually, then remove file if now empty
        fingerprints_joined = " ".join(fingerprints_to_remove)
        yield (
            f'gpg --batch --yes --no-default-keyring --keyring "{dest}"'
            f" --delete-keys {fingerprints_joined}"
        )
        yield (
            f'gpg --batch --no-default-keyring --keyring "{dest}"'
            f' --list-keys 2>/dev/null | grep -q "^pub" || rm -f "{dest}"'
        )


def _remove_keyring_file(dest: str):
    """Remove an entire keyring file."""
    yield from files.file._inner(
        path=dest,
        present=False,
    )


def _validate_installation_params(
    src: str | None, keyserver: str | None, keyid: str | list[str] | None, dest: str | None
):
    """Validate parameters for key installation."""
    if not src and not keyserver:
        raise OperationError("Either `src` or `keyserver` must be provided for installation")

    if keyserver and not keyid:
        raise OperationError("`keyid` must be provided with `keyserver`")

    if keyid and not keyserver and not src:
        raise OperationError(
            "When using `keyid` for installation, either `keyserver` or `src` must be provided"
        )

    if dest is None:
        raise OperationError("`dest` must be provided for installation")


def _validate_removal_params(
    dest: str | None, keyid: str | list[str] | None, working_dirs: list[str] | None
):
    """Validate parameters for key removal."""
    if not dest and not (keyid and working_dirs):
        raise OperationError(
            "For removal, either `dest` or both `keyid` and `working_dirs` must be provided"
        )


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

    + src: filename or URL to a key (ASCII .asc or binary .gpg)
    + dest: destination path for the key file (required for installation, optional for removal)
    + keyserver: keyserver URL for fetching keys by ID
    + keyid: key ID or list of key IDs (required with keyserver, optional for removal)
    + dearmor: whether to convert ASCII armored keys to binary format
    + mode: file permissions for the installed key
    + present: whether the key should be present (True) or absent (False)
    + working_dirs: dirs to search for existing keyrings (required for removal without dest).
      When False: if dest is provided, removes from specific keyring;
      if dest is None, removes from keyrings found in working_dirs;
      if keyid is provided, removes specific key(s);
      if keyid is None, removes entire keyring file(s)

    **Examples:**

    .. code:: python

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

    # Handle removal operations
    if present is False:
        _validate_removal_params(dest, keyid, working_dirs)

        if not dest and keyid:
            # Remove key(s) from all keyrings found in specified directories
            if not working_dirs:
                raise OperationError(
                    "`working_dirs` must be provided when removing keys without `dest`"
                )
            yield from _remove_key_from_keyrings(keyid, working_dirs)

        elif dest and keyid:
            # Remove specific key(s) from a specific keyring file
            yield from _remove_key_from_keyring(keyid, dest)

        elif dest and not keyid:
            # Remove entire keyring file
            yield from _remove_keyring_file(dest)

        else:
            raise OperationError("Invalid parameters for removal operation")

        return

    # Handle installation operations
    _validate_installation_params(src, keyserver, keyid, dest)

    # After validation, we know dest is not None for installation
    assert dest is not None, "dest should not be None after validation"

    # Check if key already exists (for idempotence)
    if keyid:
        # If we have keyid(s), check if they exist in the destination keyring
        try:
            dest_dir = str(PurePosixPath(dest).parent)
            keyring_fact = host.get_fact(GpgKeyrings, [dest_dir])

            # keyring_fact contains keyring paths as keys
            # Check if our destination keyring exists in the fact
            keyring_info = keyring_fact.get(dest)

            if keyring_info:
                existing_keys = keyring_info["keys"]
                keyids_to_check = keyid if isinstance(keyid, list) else [keyid]

                # Check if all requested keys already exist
                all_keys_exist = True
                for kid in keyids_to_check:
                    # Remove 0x prefix if present for comparison
                    clean_keyid = kid.replace("0x", "").replace("0X", "").upper()
                    key_exists = any(
                        clean_keyid in existing_key_id.upper()
                        or existing_key_id.upper().endswith(clean_keyid)
                        for existing_key_id in existing_keys.keys()
                    )
                    if not key_exists:
                        all_keys_exist = False
                        break

                if all_keys_exist:
                    # All keys already exist, ensure file permissions are correct
                    yield from files.file._inner(
                        path=dest,
                        mode=mode,
                        present=True,
                    )
                    host.noop(f"GPG keys {keyid} already exist in {dest}")
                    return
        except (KeyError, AttributeError):
            # Fact not available or incomplete, proceed with installation
            pass
    else:
        # If no keyid specified, check if destination file exists (for file/URL sources)
        try:
            file_fact = host.get_fact(file_facts.File, dest)
            if file_fact:
                # File exists, ensure permissions are correct
                yield from files.file._inner(
                    path=dest,
                    mode=mode,
                    present=True,
                )
                host.noop(f"GPG keyring {dest} already exists")
                return
        except (KeyError, AttributeError):
            # Fact not available, proceed with installation
            pass

    # Ensure destination directory exists
    dest_dir = str(PurePosixPath(dest).parent)
    yield from files.directory._inner(
        path=dest_dir,
        mode="0755",
        present=True,
    )

    # Install from source (file or URL)
    if src:
        yield from _install_key_from_src(src, dest, dearmor, mode)

    # Install from keyserver
    if keyserver:
        assert keyid is not None, "keyid should not be None after validation"
        yield from _install_key_from_keyserver(keyserver, keyid, dest, mode)


@operation()
def dearmor(src: str, dest: str, mode: str = "0644"):
    """
    Convert ASCII armored GPG key to binary format.

    + src: source ASCII armored key file
    + dest: destination binary key file
    + mode: file permissions for the output file

    **Example:**

    .. code:: python

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
