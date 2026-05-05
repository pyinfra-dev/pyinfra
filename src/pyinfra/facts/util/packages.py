"""
Unified package data model for all package managers.

Provides a common :class:`PackageInfo` dataclass and :class:`PackageStatus`
enum so that package facts can return rich, structured data instead of plain
``dict[str, set[str]]``.
"""

from dataclasses import dataclass
from enum import Enum


class PackageStatus(Enum):
    """Status of an installed package."""

    INSTALLED = "installed"
    UPGRADEABLE = "upgradeable"
    HELD = "held"


@dataclass(frozen=True)
class PackageInfo:
    """Unified package information returned by enriched package facts."""

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

    + installed: installed packages from a fact (name to set of versions).
    + upgradeable: packages with available upgrades (name to available version).
    + held: names of held/locked/pinned packages.
    """

    result: dict[str, PackageInfo] = {}
    _upgradeable = upgradeable or {}
    _held = held or set()

    for name, versions in installed.items():
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
