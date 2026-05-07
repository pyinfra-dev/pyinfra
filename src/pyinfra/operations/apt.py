"""
Manage apt packages and repositories.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from pyinfra import host
from pyinfra.api import operation
from pyinfra.facts.apt import (
    AptSources,
    SimulateOperationWillChange,
    noninteractive_apt,
    parse_apt_repo,
)
from pyinfra.facts.deb import DebPackage, DebPackages
from pyinfra.facts.files import File
from pyinfra.facts.server import Date
from pyinfra.operations import files, gpg

from .util.packaging import ensure_packages

APT_UPDATE_FILENAME = "/var/lib/apt/periodic/update-success-stamp"
APT_KEYRING_DIRS = ["/etc/apt/trusted.gpg.d", "/etc/apt/keyrings", "/usr/share/keyrings"]


def _simulate_then_perform(command: str):
    changes = host.get_fact(SimulateOperationWillChange, command)

    if not changes:
        # Simulating apt-get command failed, so the actual
        # operation will probably fail too:
        yield noninteractive_apt(command)
    elif (
        changes["upgraded"] == 0
        and changes["newly_installed"] == 0
        and changes["removed"] == 0
        and changes["not_upgraded"] == 0
    ):
        host.noop(f"{command} skipped, no changes would be performed")
    else:
        yield noninteractive_apt(command)


def _sanitize_keyring_part(name: str) -> str:
    """
    Produce a filesystem-friendly segment from a URL host, basename, or key ID.
    """
    name = name.strip().lower()
    name = re.sub(r"[^\w.-]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_.")
    return name or "apt-keyring"


def _derive_dest_from_src_and_keyids(src: str | None, keyids: list[str] | None) -> str:
    """
    Compute a stable destination path in /etc/apt/keyrings/ from a source or key IDs.

    Priority:
      1) from src (URL domain + basename, or local basename)
      2) from keyids (joined)
      3) fallback "apt-keyring.gpg"
    """
    base = None
    if src:
        parsed = urlparse(src)
        if parsed.scheme and parsed.netloc:
            domain_part = _sanitize_keyring_part(parsed.netloc.replace(":", "_"))
            bn = _sanitize_keyring_part(
                (parsed.path.rsplit("/", 1)[-1] or "key").replace(".asc", "").replace(".gpg", "")
            )
            base = f"{domain_part}-{bn}"
        else:
            bn = _sanitize_keyring_part(
                src.rsplit("/", 1)[-1].replace(".asc", "").replace(".gpg", "")
            )
            base = bn or "key"
    elif keyids:
        base = "keyserver-" + _sanitize_keyring_part("-".join(keyids))
    else:
        base = "apt-keyring"

    return f"/etc/apt/keyrings/{base}.gpg"


@operation()
def key(
    src: str | None = None,
    keyserver: str | None = None,
    keyid: str | list[str] | None = None,
    dest: str | None = None,
    present: bool = True,
):
    """
    Add or remove APT GPG keys using modern keyring management (no ``apt-key``).

    Keys are written to ``/etc/apt/keyrings/`` and can be referenced in source entries
    via ``signed-by=``. The destination filename is derived automatically from the source
    URL or key IDs when not specified explicitly.

    + src: filename or URL to a key (``.asc`` ASCII-armored or binary ``.gpg``)
    + keyserver: keyserver URL for fetching keys by ID
    + keyid: key ID or list of key IDs (required with ``keyserver``, optional for removal)
    + dest: destination filename or absolute path — ``.gpg`` extension is enforced;
      relative names are resolved under ``/etc/apt/keyrings/``
    + present: whether the key should be present (default: ``True``) or removed

    .. note::
        ASCII-armored keys (``.asc``) are automatically dearmored on installation.
        Keyserver fetches use a temporary ``GNUPGHOME`` and export binary keyrings.
        Removal without ``keyid`` deletes the whole keyring file; with ``keyid`` it
        removes individual keys and prunes empty files.

    .. warning::
        ``apt-key`` is deprecated in Debian. This operation follows the modern approach:
        https://wiki.debian.org/DebianRepository/UseThirdParty

    **Examples:**

    .. code:: python

        from pyinfra.operations import apt
        # Note: If using URL, wget is assumed to be installed.

        apt.key(
            name="Add Docker apt GPG key",
            src="https://download.docker.com/linux/debian/gpg",
            dest="docker.gpg",
        )

        apt.key(
            name="Remove specific keyring file",
            dest="old-vendor.gpg",
            present=False,
        )

        apt.key(
            name="Remove key by ID from all APT keyrings",
            keyid="0xCOMPROMISED123",
            present=False,
        )

        apt.key(
            name="Fetch keys from keyserver",
            keyserver="hkps://keyserver.ubuntu.com",
            keyid=["0xD88E42B4", "0x7EA0A9C3"],
            dest="vendor-archive.gpg",
        )
    """

    # Special case: remove by key ID without explicit destination → search all APT keyring dirs
    if not present and keyid and not dest and not src and not keyserver:
        yield from gpg.key._inner(
            keyid=keyid,
            present=False,
            working_dirs=APT_KEYRING_DIRS,
        )
        return

    # Resolve destination path under /etc/apt/keyrings/
    if dest and not dest.startswith("/"):
        dest = f"/etc/apt/keyrings/{dest}"
    elif not dest:
        if src:
            dest = _derive_dest_from_src_and_keyids(src, None)
        elif keyserver and keyid:
            keyid_list = [keyid] if isinstance(keyid, str) else keyid
            dest = _derive_dest_from_src_and_keyids(None, keyid_list)
        else:
            dest = "/etc/apt/keyrings/apt-key.gpg"

    # Delegate everything to gpg.key with APT-specific defaults
    yield from gpg.key._inner(
        src=src,
        dest=dest,
        keyserver=keyserver,
        keyid=keyid,
        present=present,
        dearmor=True,
        mode="0644",
    )


@operation()
def repo(src: str, present=True, filename: str | None = None):
    """
    Add/remove apt repositories.

    + src: apt source string eg ``deb http://X hardy main``
    + present: whether the repo should exist on the system
    + filename: optional filename to use ``/etc/apt/sources.list.d/<filename>.list``. By
      default uses ``/etc/apt/sources.list``.

    **Example:**

    .. code:: python

        apt.repo(
            name="Install VirtualBox repo",
            src="deb https://download.virtualbox.org/virtualbox/debian bionic contrib",
        )
    """

    # Get the target .list file to manage
    if filename:
        filename = "/etc/apt/sources.list.d/{0}.list".format(filename)
    else:
        filename = "/etc/apt/sources.list"

    # Work out if the repo exists already
    apt_sources = host.get_fact(AptSources)

    is_present = False
    repo = parse_apt_repo(src)
    if repo and repo in apt_sources:
        is_present = True

    # Doesn't exist and we want it
    if not is_present and present:
        yield from files.line._inner(
            path=filename,
            line=src,
            escape_regex_characters=True,
        )

    # Exists and we don't want it
    elif is_present and not present:
        yield from files.line._inner(
            path=filename,
            line=src,
            present=False,
            escape_regex_characters=True,
        )
    else:
        host.noop(
            'apt repo "{0}" {1}'.format(
                src,
                "exists" if present else "does not exist",
            ),
        )


@operation(is_idempotent=False)
def ppa(src: str, present=True):
    """
    Add/remove Ubuntu ppa repositories.

    + src: the PPA name (full ppa:user/repo format)
    + present: whether it should exist

    Note:
        requires ``apt-add-repository`` on the remote host

    **Example:**

    .. code:: python

        # Note: Assumes software-properties-common is installed.
        apt.ppa(
            name="Add the Bitcoin ppa",
            src="ppa:bitcoin/bitcoin",
        )

    """

    if present:
        yield 'apt-add-repository -y "{0}"'.format(src)

    if not present:
        yield 'apt-add-repository -y --remove "{0}"'.format(src)


@operation()
def deb(src: str, present=True, force=False):
    """
    Add/remove ``.deb`` file packages.

    + src: filename or URL of the ``.deb`` file
    + present: whether or not the package should exist on the system
    + force: whether to force the package install by passing `--force-yes` to apt

    Note:
        When installing, ``apt-get install -f`` will be run to install any unmet
        dependencies.

    URL sources with ``present=False``:
        If the ``.deb`` file isn't downloaded, pyinfra can't remove any existing
        package as the file won't exist until mid-deploy.

    **Example:**

    .. code:: python

        # Note: Assumes wget is installed.
        apt.deb(
            name="Install Chrome via deb",
            src="https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb",
        )
    """

    original_src = src

    # If source is a url
    if urlparse(src).scheme:
        # Generate a temp filename
        temp_filename = host.get_temp_filename(src)

        # Ensure it's downloaded
        yield from files.download._inner(src=src, dest=temp_filename)

        # Override the source with the downloaded file
        src = temp_filename

    # Check for file .deb information (if file is present)
    info = host.get_fact(DebPackage, package=src)
    current_packages = host.get_fact(DebPackages)

    exists = False

    # We have deb info! Check against installed packages
    if info and info.get("version") in current_packages.get(info.get("name"), {}):
        exists = True

    # Package does not exist and we want?
    if present:
        if not exists:
            # Install .deb file - ignoring failure (on unmet dependencies)
            yield "dpkg --force-confdef --force-confold -i {0} 2> /dev/null || true".format(src)
            # Attempt to install any missing dependencies
            yield "{0} -f".format(noninteractive_apt("install", force=force))
            # Now reinstall, and critically configure, the package - if there are still
            # missing deps, now we error
            yield "dpkg --force-confdef --force-confold -i {0}".format(src)
        else:
            host.noop("deb {0} is installed".format(original_src))

    # Package exists but we don't want?
    if not present:
        if exists:
            yield "{0} {1}".format(
                noninteractive_apt("remove", force=force),
                info["name"],
            )
        else:
            host.noop("deb {0} is not installed".format(original_src))


@operation(
    is_idempotent=False,
    idempotent_notice=(
        "This operation will always execute commands "
        "unless the ``cache_time`` argument is provided."
    ),
)
def update(cache_time: int | None = None):
    """
    Updates apt repositories.

    + cache_time: cache updates for this many seconds

    **Example:**

    .. code:: python

        apt.update(
            name="Update apt repositories",
            cache_time=3600,
        )
    """

    # If cache_time check when apt was last updated, prevent updates if within time
    if cache_time:
        # Ubuntu provides this handy file
        cache_info = host.get_fact(File, path=APT_UPDATE_FILENAME)

        if cache_info and cache_info["mtime"]:
            # The fact Date contains the date of the server in its timezone.
            # cache_info["mtime"] ignores the timezone and consider the timestamp as UTC.
            # So let's do the same here for the server current Date : ignore the
            # timezone and consider it as UTC to have correct comparison with
            # cache_info["mtime].
            host_utc_current_time = datetime.fromtimestamp(
                host.get_fact(Date).timestamp(), timezone.utc
            ).replace(tzinfo=None)
            host_cache_time = host_utc_current_time - timedelta(seconds=cache_time)
            if cache_info["mtime"] > host_cache_time:
                host.noop("apt is already up to date")
                return

    yield "apt-get update"

    # Some apt systems (Debian) have the /var/lib/apt/periodic directory, but
    # don't bother touching anything in there - so pyinfra does it, enabling
    # cache_time to work.
    if cache_time:
        yield "touch {0}".format(APT_UPDATE_FILENAME)


_update = update  # noqa: E305


@operation()
def upgrade(auto_remove: bool = False):
    """
    Upgrades all apt packages.

    + auto_remove: removes transitive dependencies that are no longer needed.

    **Example:**

    .. code:: python

        # Upgrade all packages
        apt.upgrade(
            name="Upgrade apt packages",
        )

        # Upgrade all packages and remove unneeded transitive dependencies
        apt.upgrade(
            name="Upgrade apt packages and remove unneeded dependencies",
            auto_remove=True
        )
    """

    command = ["upgrade"]

    if auto_remove:
        command.append("--autoremove")

    yield from _simulate_then_perform(" ".join(command))


_upgrade = upgrade  # noqa: E305 (for use below where update is a kwarg)


@operation()
def dist_upgrade(auto_remove: bool = False):
    """
    Updates all apt packages, employing dist-upgrade.

    + auto_remove: removes transitive dependencies that are no longer needed.

    **Example:**

    .. code:: python

        apt.dist_upgrade(
            name="Upgrade apt packages using dist-upgrade",
        )
    """

    command = ["dist-upgrade"]

    if auto_remove:
        command.append("--autoremove")

    yield from _simulate_then_perform(" ".join(command))


@operation()
def packages(
    packages: str | list[str] | None = None,
    present=True,
    latest=False,
    update=False,
    cache_time: int | None = None,
    upgrade=False,
    force=False,
    no_recommends=False,
    allow_downgrades=False,
    purge=False,
    extra_install_args: str | None = None,
    extra_uninstall_args: str | None = None,
):
    """
    Install/remove/update packages & update apt.

    + packages: list of packages to ensure
    + present: whether the packages should be installed
    + latest: whether to upgrade packages without a specified version
    + update: run ``apt update`` before installing packages
    + cache_time: when used with ``update``, cache for this many seconds
    + upgrade: run ``apt upgrade`` before installing packages
    + force: whether to force package installs by passing `--force-yes` to apt
    + no_recommends: don't install recommended packages
    + allow_downgrades: allow downgrading packages with version (--allow-downgrades)
    + purge: when removing packages (``present=False``) use ``apt purge`` so configuration files
      are removed alongside the package
    + extra_install_args: additional arguments to the apt install command
    + extra_uninstall_args: additional arguments to the apt uninstall command

    Versions:
        Package versions can be pinned like apt: ``<pkg>=<version>``

    Cache time:
        When ``cache_time`` is set the ``/var/lib/apt/periodic/update-success-stamp`` file
        is touched upon successful update. Some distros already do this (Ubuntu), but others
        simply leave the periodic directory empty (Debian).

    **Examples:**

    .. code:: python

        # Update package list and install packages
        apt.packages(
            name="Install Asterisk and Vim",
            packages=["asterisk", "vim"],
            update=True,
        )

        # Install the latest versions of packages (always check)
        apt.packages(
            name="Install latest Vim",
            packages=["vim"],
            latest=True,
        )

        # Note: host.get_fact(OsVersion) is the same as `uname -r` (ex: '4.15.0-72-generic')
        apt.packages(
            name="Install kernel headers",
            packages=[f"linux-headers-{host.get_fact(OsVersion)}"],
            update=True,
        )
    """

    if update:
        yield from _update._inner(cache_time=cache_time)

    if upgrade:
        yield from _upgrade._inner()

    install_command_args = ["install"]
    if no_recommends is True:
        install_command_args.append("--no-install-recommends")
    if allow_downgrades:
        install_command_args.append("--allow-downgrades")

    upgrade_command = " ".join(install_command_args)

    if extra_install_args:
        install_command_args.append(extra_install_args)

    install_command = " ".join(install_command_args)

    uninstall_command_args = ["purge" if purge else "remove"]
    if extra_uninstall_args:
        uninstall_command_args.append(extra_uninstall_args)

    uninstall_command = " ".join(uninstall_command_args)

    # Compare/ensure packages are present/not
    yield from ensure_packages(
        host,
        packages,
        host.get_fact(DebPackages),
        present,
        install_command=noninteractive_apt(install_command, force=force),
        uninstall_command=noninteractive_apt(uninstall_command, force=force),
        upgrade_command=noninteractive_apt(upgrade_command, force=force),
        version_join="=",
        latest=latest,
    )
