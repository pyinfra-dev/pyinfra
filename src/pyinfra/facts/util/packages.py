"""
Unified package data model for all package managers.

Provides a common ``PackageInfo`` dataclass and ``PackageStatus`` enum so that
package facts can return rich, structured data instead of plain
``dict[str, set[str]]``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PackageStatus(Enum):
    """Status of an installed package."""

    INSTALLED = "installed"  # installed, up-to-date (or upgrade status unknown)
    UPGRADEABLE = "upgradeable"  # installed, newer version available
    HELD = "held"  # installed but held/locked/pinned — won't be upgraded


@dataclass(frozen=True)
class PackageInfo:
    """Unified package information returned by enriched package facts.

    .. code:: python

        PackageInfo(
            name="vim",
            installed_version="9.0.1000-1",
            available_version="9.0.1100-1",
            status=PackageStatus.UPGRADEABLE,
        )
    """

    name: str
    installed_version: str
    available_version: str | None = None
    status: PackageStatus = PackageStatus.INSTALLED


def build_package_map(
    installed: dict[str, set[str]],
    upgradeable: dict[str, str] | None = None,
    held: set[str] | None = None,
) -> dict[str, PackageInfo]:
    """Build a :class:`PackageInfo` map by combining sub-fact data.

    Args:
        installed: Installed packages from an existing fact (name → set of versions).
        upgradeable: Packages with available upgrades (name → available version).
        held: Names of held/locked packages.

    Returns:
        Unified map of name → :class:`PackageInfo`.
    """

    result: dict[str, PackageInfo] = {}
    _upgradeable = upgradeable or {}
    _held = held or set()

    for name, versions in installed.items():
        # Facts typically return a single version per package
        version = next(iter(versions), "")

        if name in _held:
            status = PackageStatus.HELD
        elif name in _upgradeable:
            status = PackageStatus.UPGRADEABLE
        else:
            status = PackageStatus.INSTALLED

        result[name] = PackageInfo(
            name=name,
            installed_version=version,
            available_version=_upgradeable.get(name),
            status=status,
        )

    return result
