"""
.. warning::
    This module is deprecated and will be removed in future version of pyinfra.
    Use [openwrt.opkg](../operations/openwrt.md) or [openwrt.packages](../operations/openwrt.md)
    instead.

Gather the information provided by
[opkg](https://openwrt.org/docs/guide-user/additional-software/opkg) on OpenWrt systems:
"""

from pyinfra.facts.openwrt.opkg import (
    OpkgConf as OpenWrtConf,
    OpkgFeeds as OpenWrtFeeds,
    OpkgInstallableArchitectures as OpenWrtInstallableArchitectures,
    OpkgPackages as OpenWrtPackages,
    OpkgUpgradeablePackages as OpenWrtUpgradeablePackages,
)


class OpkgConf(OpenWrtConf):
    """
    See [openwrt.opkg.OpkgConf](../facts/openwrt.md#openwrt-opkg.OpkgConf) for details.
    """

    is_deprecated = True
    deprecated_for = "openwrt.opkg.OpkgConf"


class OpkgFeeds(OpenWrtFeeds):
    """
    See [openwrt.opkg.OpkgFeeds](../facts/openwrt.md#openwrt-opkg.OpkgFeeds) for details.
    """

    is_deprecated = True
    deprecated_for = "openwrt.opkg.OpkgFeeds"


class OpkgInstallableArchitectures(OpenWrtInstallableArchitectures):
    """
    See [openwrt.opkg.OpkgInstallableArchitectures](../facts/openwrt.md#openwrt-opkg.OpkgInstallableArchitectures) for details.
    """

    is_deprecated = True
    deprecated_for = "openwrt.opkg.OpkgInstallableArchitectures"


class OpkgPackages(OpenWrtPackages):
    """
    See [openwrt.opkg.OpkgPackages](../facts/openwrt.md#openwrt-opkg.OpkgPackages) for details.
    """

    is_deprecated = True
    deprecated_for = "openwrt.opkg.OpkgPackages"


class OpkgUpgradeablePackages(OpenWrtUpgradeablePackages):
    """
    See [openwrt.opkg.OpkgUpgradeablePackages](../facts/openwrt.md#openwrt-opkg.OpkgUpgradeablePackages) for details.
    """

    is_deprecated = True
    deprecated_for = "openwrt.opkg.OpkgUpgradeablePackages"
