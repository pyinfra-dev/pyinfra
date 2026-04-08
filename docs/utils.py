import re
from inspect import getmembers, ismodule
from pathlib import Path
from types import ModuleType
from typing import Generator, Any


def title_line(char, string):
    return "".join(char for _ in range(0, len(string)))


def format_doc_line(line):
    # Bold the <arg>: part of each line, escaping * prefixes for RST compatibility
    def _bold_arg(m):
        stars = m.group(1).replace("*", "\\*")
        return f"+ **{stars}{m.group(2)}**{m.group(3)}"

    line = re.sub(r"\+ (\*{0,2})([0-9a-z_\/]+)(.*)", _bold_arg, line)

    # Python's __doc__ attribute already dedents docstrings, so we don't need to strip anything
    return line


def including_sub_modules(module: ModuleType) -> Generator[ModuleType]:
    """Yield all modules to be examined, including the base modules."""
    yield module
    module_name = module.__name__
    for key, value in getmembers(module):
        if (
            ismodule(value)
            and value.__name__.startswith(module_name)
            and (not key.startswith("__"))
        ):
            yield from including_sub_modules(value)


def get_module_names(
    src_dir: Path,
    *,
    exclude_dir: str | list[str] | None = None,
    exclude_file: str | list[str] | None = None,
) -> list[str]:
    """Return file names of all modules found in src_dir."""
    exclude_path = set(exclude_dir or ["util", "__pycache__"])
    exclude_name = set(exclude_file or ["__init__.py"])

    module_names = [
        path.stem
        for path in (src_dir.iterdir())
        if (
            (path.is_dir() and (path.name not in exclude_path))
            or ((path.suffix == ".py") and (path.name not in exclude_name))
        )
    ]
    return module_names


def remove_dups(all: list[tuple[str, Any]]) -> list[tuple[str, Any]]:
    """Remove items with duplicate values, i.e. the same function or module found again."""
    unique, seen = [], set()
    for key, value in all:
        if value not in seen:
            seen.add(value)
            unique.append((key, value))
    return unique
