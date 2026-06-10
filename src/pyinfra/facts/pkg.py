from __future__ import annotations

import re

from typing_extensions import override

from pyinfra.api import FactBase

from .util.packages import PackageInfo, build_package_map

# Separates installed-package lines from the `pkg version` remote comparison
# lines in the compound command output below.
_REMOTE_MARKER = "__pyinfra_pkg_remote__"

_REMOTE_HAS_RE = re.compile(r"\(remote has ([^)]+)\)")


class PkgPackages(FactBase[list[PackageInfo]]):
    """
    Returns a list of installed pkg packages as ``PackageInfo``, sorted by
    name. On FreeBSD (``pkg``) entries carry the locked status (``HELD``, via
    ``pkg lock``) and available upgrades (``UPGRADEABLE``, compared against
    the remote catalogues). With the ``pkg_info`` fallback used on other BSDs
    every entry is ``INSTALLED``.

    .. code:: python

        [
            PackageInfo(
                name="zsh",
                installed_versions=("5.9_5",),
                available_version="5.9_6",
                status=PackageStatus.UPGRADEABLE,
            ),
        ]
    """

    regex = r"^([a-zA-Z0-9_\-\+]+)\-([0-9a-z\.]+)"
    default = list

    @override
    def command(self) -> str:
        return (
            f"(pkg query '%n %v %k' && echo {_REMOTE_MARKER} && (pkg version -vRL= || true))"
            " || pkg_info || true"
        )

    @override
    def process(self, output: list[str]) -> list[PackageInfo]:
        installed: dict[str, set[str]] = {}
        upgradeable: dict[str, str] = {}
        held: set[str] = set()

        # The marker only appears when `pkg query` ran, so its presence tells
        # us whether to parse `name version locked` fields or pkg_info lines.
        is_pkg_query = any(line.strip() == _REMOTE_MARKER for line in output)

        in_remote = False
        for line in output:
            if line.strip() == _REMOTE_MARKER:
                in_remote = True
                continue

            if in_remote:
                # `pkg version -vRL=` line: `name-version  <  needs updating (remote has X)`
                parts = line.split()
                if len(parts) >= 2 and parts[1] == "<":
                    match = _REMOTE_HAS_RE.search(line)
                    if match:
                        upgradeable[parts[0].rsplit("-", 1)[0]] = match.group(1)
                continue

            if is_pkg_query:
                # `pkg query '%n %v %k'` line: `name version locked(0|1)`
                parts = line.split()
                if len(parts) == 3 and parts[2] in ("0", "1"):
                    name, version, locked = parts
                    installed.setdefault(name, set()).add(version)
                    if locked == "1":
                        held.add(name)
            else:
                match = re.match(self.regex, line)
                if match:
                    installed.setdefault(match.group(1), set()).add(match.group(2))

        return build_package_map(installed, upgradeable, held)
