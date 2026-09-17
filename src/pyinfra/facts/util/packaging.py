from __future__ import annotations

import json
import re
from collections.abc import Iterable

PackageVersionDict = dict[str, set[str]]


def pip_report_is_satisfied(output: Iterable[str]) -> bool:
    """Whether a ``pip install --dry-run --report -`` JSON report would change nothing.

    Returns ``True`` only when the report parses and lists no packages to install. Any
    parse failure or resolver error is treated as "not satisfied" so the real install runs
    (and surfaces the error).
    """
    try:
        report = json.loads("\n".join(output))
    except (json.JSONDecodeError, TypeError):
        return False
    if not isinstance(report, dict):
        return False
    return len(report.get("install", [None])) == 0


def uv_dry_run_is_satisfied(output: Iterable[str]) -> bool:
    """Whether a ``uv pip install --dry-run`` run would change nothing.

    uv prints ``Would make no changes`` when the environment already satisfies the request.
    """
    return any("Would make no changes" in line for line in output)


def parse_packages(regex: str, output: Iterable[str]) -> PackageVersionDict:
    packages: dict[str, set[str]] = {}

    for line in output:
        matches = re.match(regex, line)

        if matches:
            name = matches.group(1)
            packages.setdefault(name, set())
            packages[name].add(matches.group(2))

    return packages


REPO_FILENAME_MARKER = "#pyinfra-filename:"


def _parse_yum_or_zypper_repositories(output):
    repos = []

    current_repo: dict[str, str] = {}
    current_file: str | None = None
    for line in output:
        line = line.strip()
        if not line:
            continue

        if line.startswith(REPO_FILENAME_MARKER):
            if current_repo:
                repos.append(current_repo)
                current_repo = {}
            current_file = line[len(REPO_FILENAME_MARKER) :].strip() or None
            continue

        if line.startswith("#"):
            continue

        if line.startswith("["):
            if current_repo:
                repos.append(current_repo)
                current_repo = {}

            current_repo["repoid"] = line[1:-1]
            current_repo["name"] = line[1:-1]
            if current_file is not None:
                current_repo["filename"] = current_file

        if current_repo and "=" in line:
            key, value = re.split(r"\s*=\s*", line, maxsplit=1)
            current_repo[key] = value

    if current_repo:
        repos.append(current_repo)

    return repos


parse_yum_repositories = _parse_yum_or_zypper_repositories

parse_zypper_repositories = _parse_yum_or_zypper_repositories
