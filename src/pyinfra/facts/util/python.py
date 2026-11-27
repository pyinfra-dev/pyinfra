from __future__ import annotations

import re

PYTHON_VERSION_REGEX = re.compile(r"^(\d+)\.(\d+)\.(\d+)")


def parse_python_version(output: list[str]) -> tuple[int, int, int] | None:
    """
    Parse the first line of ``output`` that starts with a ``major.minor.micro`` version into a
    tuple of ints, eg ``3.14.0rc1`` -> ``(3, 14, 0)``. Returns ``None`` when there is none.
    """
    for line in output:
        match = PYTHON_VERSION_REGEX.match(line.strip())
        if match:
            major, minor, micro = match.groups()
            return int(major), int(minor), int(micro)
    return None
