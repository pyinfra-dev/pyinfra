"""
This module is deprecated and will be removed in future version of pyinfra.
Use ``openwrt.opkg`` or ``openwrt.packages`` instead.

Manage packages on OpenWrt using opkg
    + ``update`` - update local copy of package information
    + ``packages`` -  install and remove packages
"""

from pyinfra.api import operation
from pyinfra.operations.openwrt.opkg import packages as openwrt_packages, update as openwrt_update


@operation(is_deprecated=True, deprecated_for="openwrt.opkg.packages or openwrt.packages")
def packages(
    packages: str | list[str] = "",
    present: bool = True,
    latest: bool = False,
    update: bool = True,
):
    """
    Install, update or remove the specified packages.
    """
    yield from openwrt_packages._inner(  # noqa: SLF001
        packages=packages, present=present, latest=latest, update=update
    )


@operation(is_idempotent=False, deprecated_for="openwrt.opkg.update or openwrt.update")
def update():
    """
    Update the local package information.
    """

    yield from openwrt_update._inner()  # noqa: SLF001
