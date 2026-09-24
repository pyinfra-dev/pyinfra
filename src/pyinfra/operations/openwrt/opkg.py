"""
Manage packages on OpenWrt using opkg
    + `packages` -  install and remove packages
    + `update` - update local copy of package information

See https://openwrt.org/docs/guide-user/additional-software/opkg

OpenWrt recommends against upgrading all packages  thus there is no `opkg.upgrade` function

.. note::
    as of OpenWrt [Release 25.12](https://openwrt.org/releases/25.12/notes-25.12.0#switch_package_manager_from_opkg_to_apk)
    OpenWrt uses [apk](../operations/apk.md)

    note: this does _not_ show up in the online documentation; the file header in __init__.py does
and thus the note above is repeated in each operation.
"""

from pyinfra import host
from pyinfra.api import StringCommand, operation
from pyinfra.facts.openwrt.opkg import OpkgPackages
from pyinfra.operations.util.packaging import ensure_packages

EQUALS = "="


@operation(is_idempotent=False)
def update():
    """
    Update the local opkg information.
    """

    yield StringCommand("opkg update")


_update = update


@operation()
def packages(
    packages: str | list[str] | None = None,
    present: bool = True,
    latest: bool = False,
    update: bool = True,
):
    """
    Add/remove/update opkg packages.

    + packages: package or list of packages to that must/must not be present
    + present: whether the package(s) should be installed or removed (default ``True``).
    + latest: whether to attempt to upgrade the specified package(s) (default ``False``).
    + update: run ``opkg update`` before installing packages (default ``True``).

    **Not Supported:**
        ``opkg`` does not support version pinning, i.e. ``<pkg>=<version>`` is _not_ allowed
        and will cause an exception.

    **Examples:**

    .. code:: python

        from pyinfra.operations import opkg

        # Ensure packages are installed (will not force package upgrade)
        openwrt.opkg.packages(['asterisk', 'vim'], name="Install Asterisk and Vim")

        # Install the latest versions of packages (always check)
        openwrt.opkg.packages(
            'vim',
            latest=True,
            name="Ensure we have the latest version of Vim"
        )

    .. note::
      as of OpenWrt [Release 25.12](https://openwrt.org/releases/25.12/notes-25.12.0#switch_package_manager_from_opkg_to_apk)
      OpenWrt uses [apk](../operations/apk.md)
    """
    pkg_list = [packages] if isinstance(packages, str) else (packages or [])
    if (len(pkg_list) < 1) or any((len(p) < 1) or (p is None) for p in pkg_list):
        host.noop("empty or invalid package list provided to openwrt.opkg.packages")
        return

    have_equals = ",".join([pkg.split(EQUALS)[0] for pkg in pkg_list if EQUALS in pkg])
    if len(have_equals) > 0:
        raise ValueError(f"opkg does not support version pinning but found for: '{have_equals}'")

    if update:
        yield from _update._inner()  # noqa: SLF001

    yield from ensure_packages(
        host,
        pkg_list,
        host.get_fact(OpkgPackages),
        present,
        install_command="opkg install",
        upgrade_command="opkg upgrade",
        uninstall_command="opkg remove",
        latest=latest,
    )
