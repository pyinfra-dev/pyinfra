"""
    Manage packages on OpenWrt using opkg (see https://openwrt.org/docs/guide-user/additional-software/opkg)
        + ``update`` - update local copy of package information
        + ``packages`` -  install and remove packages

    OpenWrt recommends against upgrading all packages  thus there is no ``opkg.upgrade`` function
"""
from __future__ import annotations

from pyinfra import host
from pyinfra.api import StringCommand, operation
from pyinfra.facts.opkg import Packages
from pyinfra.operations.util.packaging import ensure_packages

EQUALS = "="
UPDATE_ENTRY = "$$updated$$"  # use $ as not allowed in package names (TODO - need reference)


@operation(is_idempotent=False)
def update(force: bool = False):
    """
    Update the local opkg information.  Unless force is set, will only run
    once per host per invocation of pyinfra.

    + force - refresh the package list even if already done
    """

    if force or (UPDATE_ENTRY not in host.get_fact(Packages)):
        host.get_fact(Packages).update({UPDATE_ENTRY: [UPDATE_ENTRY]})
        yield StringCommand("opkg update > /dev/null 2>&1")
    else:
        host.noop("opkg packages already updated and not forced")


_update = update


@operation
def packages(
    packages: str | list[str] = "",
    present: bool = True,
    latest: bool = False,
    update: bool = True,
):
    """
    Add/remove/update opkg packages.

    + packages: package or list of packages to that must/must not be present
    + present: whether the package(s) should be installed (default True) or removed
    + latest: whether to attempt to upgrade the specified package(s) (default False)
    + update: run ``opkg update`` before installing packages (default True)

    Not Supported:
        Opkg does not support version pinning, i.e. ``<pkg>=<version>`` is not allowed
        and will cause an exception.

    **Examples:**

    .. code:: python

        # Ensure packages are installed∂ (will not force package upgrade)
        opkg.packages(['asterisk', 'vim'], name="Install Asterisk and Vim")

        # Install the latest versions of packages (always check)
        opkg.packages(
            'vim',
            latest=True,
            name="Ensure we have the latest version of Vim"
        )
    """
    if str(packages) == "" or (
        isinstance(packages, list) and (len(packages) < 1 or all(len(p) < 1 for p in packages))
    ):
        host.noop("empty or invalid package list provided to opkg.packages")
        return

    pkg_list = packages if isinstance(packages, list) else [packages]
    have_equals = ",".join([pkg.split(EQUALS)[0] for pkg in pkg_list if EQUALS in pkg])
    if len(have_equals) > 0:
        raise ValueError(f"opkg does not support version pinning but found for: '{have_equals}'")

    if update:
        yield from _update()

    yield from ensure_packages(
        host,
        pkg_list,
        host.get_fact(Packages),
        present,
        install_command="opkg install",
        upgrade_command="opkg upgrade",
        uninstall_command="opkg remove",
        latest=latest,
        # lower=True, # FIXME - does ensure_packages always do this or ?
    )
