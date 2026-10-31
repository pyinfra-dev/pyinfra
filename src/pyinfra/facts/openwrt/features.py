"""
Provides a fact that tells whether a host supports an OpenWrt feature or not.

    + whether the host uses ``apk`` (vs. ``opkg``)
    + whether the host has ``DSA`` (vs. ``swconfig``)
    + whether the host has ``FW4`` (and ``nftables`` vs. ``FW3/iptables``)

note: this does _not_ show up in the online documentation; the file header in __init__.py does
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique

from typing_extensions import override

from pyinfra import logger
from pyinfra.api import FactBase


@unique
class OpenWrtFeature(Enum):
    USES_APK = "uses_apk"
    HAS_DSA = "has_dsa"
    HAS_FW4 = "has_fw4"


@dataclass(frozen=True)
class Release:
    """
    A release with major and minor components
    """

    major: int
    minor: int


@dataclass(frozen=True)
class ReleaseRange:
    """
    A range of releases, usually used for validity.
    Any release is newer than a start of None and older than an end of None
    """

    start: Release | None
    end: Release | None

    def contains(self, release: Release) -> bool:
        return (
            (self.start is None)
            or (release.major > self.start.major)
            or ((release.major == self.start.major) and (release.minor >= self.start.minor))
        ) and (
            (self.end is None)
            or (release.major < self.end.major)
            or ((release.major == self.end.major) and (release.minor <= self.end.minor))
        )


#
# References for release ranges in FEATURES table
#
# Feature.USES_APK - https://openwrt.org/releases/25.12/notes-25.12.0#switch_package_manager_from_opkg_to_apk
# Feature.HAS_DSA - https://openwrt.org/releases/21.02/notes-21.02.0#initial_dsa_support
# Feature.HAS_FW4 - https://openwrt.org/releases/22.03/notes-22.03.0#firewall4_based_on_nftables

FEATURES = {
    OpenWrtFeature.USES_APK: ReleaseRange(Release(25, 12), None),
    # the following is a bit optimistic as it is really target-specific
    OpenWrtFeature.HAS_DSA: ReleaseRange(Release(21, 2), None),
    OpenWrtFeature.HAS_FW4: ReleaseRange(Release(22, 3), None),
}

DOES_NOT_EXIST = ReleaseRange(Release(9999, 0), Release(9999, 0))

# line in /etc/openwrt-release with release number looks like: DISTRIB_RELEASE='19.07.2'
THE_FILE = "/etc/openwrt_release"
PREFIX = "DISTRIB_RELEASE='"
SUFFIX = "'"


class OpenWrtHasFeature(FactBase[bool]):
    """
    Returns `true` if the running version of OpenWrt supports a specific feature and `false`
    otherwise.

    .. code:: python
        from pyinfra.facts.openwrt import OpenWrtFeature

        if host.get_fact(OpenWrtHasFeature, OpenWrtFeature.HAS_DSA):
            # setup configuration using the Distributed Switching Architecture
        else:
            # setup configuration using swconfig
    """

    # this isn't a ShortFact using LinuxDistribution because short facts can't have parameters

    @override
    def command(self, feature: OpenWrtFeature) -> str:
        # TODO: remove this once CLI and fact tests from fixtures support enums
        if isinstance(feature, str):
            feature = OpenWrtFeature(feature)

        return f"echo {feature.value} && cat {THE_FILE}"

    @override
    @staticmethod
    def default() -> bool:
        return False

    @override
    def process(self, output: list[str]) -> bool:
        if len(output) < 2:  # usually will be 8 but conceptually we just need 2
            logger.error(f"not enough lines of output from {THE_FILE}")
            return False

        feature = OpenWrtFeature(output[0])
        for line in output[1:]:
            if not line.startswith(PREFIX):
                continue
            if len(pieces := line.removeprefix(PREFIX).strip("'").split(".")) >= 2:
                try:
                    major, minor = int(pieces[0]), int(pieces[1])
                except (ValueError, TypeError):
                    logger.error(f"could not decode OpenWrt release from '{'.'.join(pieces)}'")
                else:
                    return FEATURES.get(feature, DOES_NOT_EXIST).contains(Release(major, minor))
            else:
                logger.error(f"unrecognized format for OpenWrt release: '{'.'.join(pieces)}'")
            break
        else:
            logger.error(f"'{PREFIX}' not found in {THE_FILE}")

        return False
