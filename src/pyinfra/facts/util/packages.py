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
from typing import Any


class PackageStatus(Enum):
    """Status of an installed package."""

    INSTALLED = "installed"
    UPGRADEABLE = "upgradeable"
    HELD = "held"


_VERSION_PART_RE = re.compile(r"\d+|\D+")


def _version_sort_key(version: str) -> tuple[tuple[int, int | str], ...]:
    """Natural-order sort key for deterministic package version display.

    Splits into runs of digits and non-digits; digit runs compare as integers
    so ``5.10`` sorts after ``5.2`` and ``9.0-1`` after ``9.0``. This is not a
    substitute for distro-specific version comparison and must not determine
    upgrade availability.
    """
    return tuple(
        (0, int(part)) if part.isdigit() else (1, part)
        for part in _VERSION_PART_RE.findall(version)
    )


@dataclass(frozen=True)
class PackageInfo:
    """Unified package information returned by enriched package facts.

    ``installed_versions`` holds every installed version in generic natural
    order. Most package managers only ever install one version of a package,
    but rpm-family installonly packages (kernels), portage SLOTs and dpkg
    multi-arch can produce more than one. :pyattr:`installed_version` returns
    the last version in that order, or ``None`` when none are reported.

    ``available_version`` and ``status`` come from the package manager. They,
    not generic version sorting, determine whether an upgrade is available.
    """

    name: str
    installed_versions: tuple[str, ...] = ()
    available_version: str | None = None
    status: PackageStatus = PackageStatus.INSTALLED

    def __post_init__(self) -> None:
        if self.status is PackageStatus.INSTALLED and self.available_version is not None:
            raise ValueError("available_version requires UPGRADEABLE or HELD status")
        if self.status is PackageStatus.UPGRADEABLE and self.available_version is None:
            raise ValueError("UPGRADEABLE status requires available_version")

    @property
    def installed_version(self) -> str | None:
        return self.installed_versions[-1] if self.installed_versions else None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PackageInfo:
        """Build a :class:`PackageInfo` from a dict-shaped description.

        This is useful for consumers that receive plain JSON-like package
        data (for example test fixtures or inventory variables) and need a
        real :class:`PackageInfo` instance. The package manager must provide
        ``UPGRADEABLE`` explicitly when an available version is present.
        Without a status, the default is ``INSTALLED``.
        """
        return cls(
            name=data["name"],
            installed_versions=tuple(data.get("installed_versions", ())),
            available_version=data.get("available_version"),
            status=PackageStatus(data.get("status", "installed")),
        )


def build_package_map(
    installed: dict[str, set[str]],
    upgradeable: dict[str, str] | None = None,
    held: set[str] | None = None,
) -> dict[str, PackageInfo]:
    """Build a :class:`PackageInfo` map by combining sub-fact data.

    + installed: installed packages from a fact (name to set of versions).
    + upgradeable: packages with available upgrades (name to available version).
    + held: names of held/locked/pinned packages.

    Versions are sorted with a generic natural-order key for deterministic
    display. Upgrade availability comes from the package manager, not this
    ordering.
    """

    result: dict[str, PackageInfo] = {}
    _upgradeable = upgradeable or {}
    _held = held or set()

    for name, versions in installed.items():
        sorted_versions = tuple(sorted(versions, key=_version_sort_key))

        if name in _held:
            status = PackageStatus.HELD
        elif name in _upgradeable:
            status = PackageStatus.UPGRADEABLE
        else:
            status = PackageStatus.INSTALLED

        result[name] = PackageInfo(
            name=name,
            installed_versions=sorted_versions,
            available_version=_upgradeable.get(name),
            status=status,
        )

    return result
