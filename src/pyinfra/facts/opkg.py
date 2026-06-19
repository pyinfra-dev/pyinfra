"""
This is deprecated: use ``openwrt.opkg`` or ``openwrt.packages`` instead.

Gather the information provided by ``opkg`` on OpenWrt systems:
    + ``opkg`` configuration
    + feeds configuration
    + list of installed packages
    + list of packages with available upgrades

"""

from pyinfra.facts.openwrt.opkg import OpkgConf as OpenWrtConf, OpkgFeeds as OpenWrtFeeds
from pyinfra.facts.openwrt.opkg import OpkgInstallableArchitectures as OpenWrtInstallableArchitectures, OpkgPackages as OpenWrtPackages
from pyinfra.facts.openwrt.opkg import OpkgUpgradeablePackages as OpenWrtUpgradeablePackages


class OpkgConf(OpenWrtConf):
    is_deprecated = True
    deprecated_for = "openwrt.opkg.OpkgConf"

class OpkgFeeds(OpenWrtFeeds):
    is_deprecated = True
    deprecated_for = "openwrt.opkg.OpkgFeeds"

class OpkgInstallableArchitectures(OpenWrtInstallableArchitectures):
    is_deprecated = True
    deprecated_for = "openwrt.opkg.OpkgInstallableArchitectures"

class OpkgPackages(OpenWrtPackages):
    is_deprecated = True
    deprecated_for = "openwrt.opkg.OpkgPackages"

class OpkgUpgradeablePackages(OpenWrtUpgradeablePackages):
    is_deprecated = True
    deprecated_for = "openwrt.opkg.OpkgUpgradeablePackages"
