# from https://stackoverflow.com/a/60708339, but with a few modifications
from __future__ import annotations  # for | in type hints

import re

units = {
    "B": 1,
    "KB": 10**3,
    "MB": 10**6,
    "GB": 10**9,
    "TB": 10**12,
    "KIB": 2**10,
    "MIB": 2**20,
    "GIB": 2**30,
    "TIB": 2**40,
}


def parse_human_readable_size(size: str) -> int:
    size = size.upper()
    if not re.match(r" ", size):
        size = re.sub(r"([KMGT]?I?[B])", r" \1", size)
    number, unit = [string.strip() for string in size.split()]
    return int(float(number) * units[unit])


def parse_size(size: str | int) -> int:
    if isinstance(size, int):
        return size
    return parse_human_readable_size(size)
