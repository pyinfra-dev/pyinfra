"""
Unified package data model for all package managers.

Provides a common :class:`PackageInfo` dataclass and :class:`PackageStatus`
enum so that package facts can return rich, structured data instead of plain
``dict[str, set[str]]``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class PackageStatus(Enum):
    """Status of an installed package."""

    INSTALLED = "installed"
    UPGRADEABLE = "upgradeable"
    HELD = "held"


_VERSION_PART_RE = re.compile(r"\d+|\D+")


def _version_sort_key(version: str) -> tuple[tuple[int, int | str], ...]:
    """Natural-order sort key for package version strings.

    Splits into runs of digits and non-digits; digit runs compare as integers
    so ``5.10`` sorts after ``5.2`` and ``9.0-1`` after ``9.0``. Good enough
    for rpm, dpkg and portage version strings as a cross-distro default; it
    is not a substitute for distro-specific vercmp.
    """
    return tuple(
        (0, int(part)) if part.isdigit() else (1, part)
        for part in _VERSION_PART_RE.findall(version)
    )


@dataclass(frozen=True)
class PackageInfo:
    """Unified package information returned by enriched package facts.

    ``installed_versions`` holds every installed version, sorted ascending so
    the highest is last. Most package managers only ever install one version
    of a package, but rpm-family installonly packages (kernels), portage
    SLOTs and dpkg multi-arch can produce more than one. The
    :pyattr:`installed_version` property returns the highest installed
    version (or ``None`` when none are reported).
    """

    name: str
    installed_versions: tuple[str, ...] = ()
    available_version: str | None = None
    status: PackageStatus = PackageStatus.INSTALLED

    @property
    def installed_version(self) -> str | None:
        return self.installed_versions[-1] if self.installed_versions else None


def _package_info_from_value(value: PackageInfo | dict) -> PackageInfo:
    """Normalize a :class:`PackageInfo` or dict-shaped value into a real instance.

    This lets callers (and tests that supply plain JSON fact fixtures) pass
    dict-like package descriptions without requiring every consumer to handle
    the conversion themselves.
    """
    if isinstance(value, PackageInfo):
        return value
    if isinstance(value, dict):
        return PackageInfo(
            name=value["name"],
            installed_versions=tuple(value.get("installed_versions", ())),
            available_version=value.get("available_version"),
            status=PackageStatus(value.get("status", "installed")),
        )
    raise TypeError(f"Cannot normalize {value!r} to PackageInfo")


def build_package_map(
    installed: dict[str, set[str]],
    upgradeable: dict[str, str] | None = None,
    held: set[str] | None = None,
) -> list[PackageInfo]:
    """Build a list of :class:`PackageInfo` by combining package data.

    + installed: installed packages (name to set of versions).
    + upgradeable: packages with available upgrades (name to available version).
    + held: names of held/locked/pinned packages.

    The result is a flat ``list[PackageInfo]`` sorted by name (each entry
    carries its own name, so a name-keyed dict would only duplicate it).
    Versions within an entry are sorted with a natural-order key (digit runs
    as integers) so multi-version output is deterministic across runs and the
    highest version is last.
    """

    result: list[PackageInfo] = []
    _upgradeable = upgradeable or {}
    _held = held or set()

    for name in sorted(installed):
        sorted_versions = tuple(sorted(installed[name], key=_version_sort_key))

        if name in _held:
            status = PackageStatus.HELD
        elif name in _upgradeable:
            status = PackageStatus.UPGRADEABLE
        else:
            status = PackageStatus.INSTALLED

        result.append(
            PackageInfo(
                name=name,
                installed_versions=sorted_versions,
                available_version=_upgradeable.get(name),
                status=status,
            )
        )

    return result
