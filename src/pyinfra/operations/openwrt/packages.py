"""
Manage packages on OpenWrt using opkg or apk depending on the `version`_ of OpenWrt.
    + ``update`` - update local copy of package information
    + ``packages`` -  install and remove packages

See https://openwrt.org/docs/guide-user/additional-software/apk and
    https://openwrt.org/docs/guide-user/additional-software/opkg

TBD - OpenWrt recommends against upgrading all packages  thus there is no ``opkg.upgrade`` function

.. _version: https://openwrt.org/releases/25.12/notes-25.12.0#switch_package_manager_from_opkg_to_apk
"""

from pyinfra import host
from pyinfra.api import operation
from pyinfra.facts.openwrt import OpenWrtFeature, OpenWrtHasFeature
from pyinfra.operations import apk

from . import opkg


@operation(is_idempotent=False)
def update():
    """
    Update the local package information.
    """
    if host.get_fact(OpenWrtHasFeature, OpenWrtFeature.USES_APK):
        yield from apk.update._inner()  # noqa: SLF001
    else:
        yield from opkg.update._inner()  # noqa: SLF001


@operation()
def packages(
    packages: str | list[str] = "",
    present: bool = True,
    latest: bool = False,
    update: bool = False,
):
    """
    Add/remove/update packages using `opkg` or `apk` depending on the OpenWrt version.

    + packages: package or list of packages to that must/must not be present
    + present: whether the package(s) should be installed (default True) or removed
    + latest: whether to attempt to upgrade the specified package(s) (default False)
    + update: run ``apk|opkg update`` before installing packages (default False)

    See TBD and TBD for more details.

    TBD - Not Supported:
        Opkg does not support version pinning, i.e. ``<pkg>=<version>`` is not allowed
        and will cause an exception.

    **Examples:**

    .. code:: python

        from pyinfra.operations import openwrt
        # Ensure packages are installed (will not force package upgrade)
        openwrt.packages(['asterisk', 'vim'], name="Install Asterisk and Vim")

        # Install the latest versions of packages
        openwrt.packages(
            'vim',
            latest=True,
            name="Ensure we have the latest version of Vim"
        )
    """
    if host.get_fact(OpenWrtHasFeature, feature=OpenWrtFeature.USES_APK):
        yield from apk.packages._inner(  # noqa: SLF001
            packages=packages, latest=latest, update=update, present=present
        )
    else:
        yield from opkg.packages._inner(  # noqa: SLF001
            packages=packages, latest=latest, update=update, present=present
        )
