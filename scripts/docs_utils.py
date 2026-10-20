import re
from inspect import cleandoc, getmembers, ismodule
from pathlib import Path
from types import ModuleType
from typing import Any
from collections.abc import Generator


def format_doc_line(line: str) -> str:
    """Bold the ``+ <arg>:`` prefix of a docstring argument line for Markdown.

    Matches ``+`` followed by an optional ``*`` or ``**`` (for ``*args``/
    ``**kwargs``), a name of ``[0-9a-z_/]``, and preserves the rest of the
    line. Stars are emitted literally since this is Markdown, not RST.
    """

    def _bold_arg(m):
        return f"+ **{m.group(1)}{m.group(2)}**{m.group(3)}"

    return re.sub(r"\+ (\*{0,2})([0-9a-z_\/]+)(.*)", _bold_arg, line)


_DIRECTIVE_RE = re.compile(
    r"^(?P<indent>\s*)\.\. (?P<kind>code|note|caution|tip|important|warning|hint|seealso|admonition)::\s*(?P<arg>.*)$"
)
_ADMONITION_KINDS = {"note", "caution", "tip", "important", "warning", "hint", "seealso"}


def rst_to_md_docstring(text: str) -> str:
    """Best-effort RST→Markdown conversion for Python docstrings.

    Handles the directives pyinfra docstrings use in practice:
    - ``.. code:: LANG`` / ``.. code::`` → fenced code block.
    - ``.. note::``, ``.. caution::`` etc. → ``!!! note`` admonitions.
    - ``.. admonition:: Title`` → ``!!! note "Title"``.
    - Double-backtick inline literals (``` ``x`` ```) → single-backtick.
    """
    if not text:
        return text

    # Inline: convert ``x`` to `x` (pymdownx.superfences handles the rest).
    text = re.sub(r"``([^`]+?)``", r"`\1`", text)

    lines = text.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = _DIRECTIVE_RE.match(line)
        if not m:
            out.append(line)
            i += 1
            continue

        indent = m.group("indent")
        kind = m.group("kind")
        arg = m.group("arg").strip()
        base_indent_len = len(indent)

        # Skip the blank line(s) between directive and its body.
        j = i + 1
        while j < len(lines) and lines[j].strip() == "":
            j += 1

        # Consume body lines (strictly indented deeper than the directive).
        body: list[str] = []
        body_indent: int | None = None
        while j < len(lines):
            bl = lines[j]
            if bl.strip() == "":
                body.append("")
                j += 1
                continue
            bl_indent = len(bl) - len(bl.lstrip())
            if bl_indent <= base_indent_len:
                break
            if body_indent is None:
                body_indent = bl_indent
            body.append(bl[min(body_indent, bl_indent) :])
            j += 1

        # Strip trailing blanks from body.
        while body and body[-1] == "":
            body.pop()

        if kind == "code":
            fence_open = f"{indent}```{arg}" if arg else f"{indent}```"
            out.append(fence_open)
            out.extend(f"{indent}{bl}" for bl in body)
            out.append(f"{indent}```")
        elif kind == "admonition":
            title = arg or "Note"
            out.append(f'{indent}!!! note "{title}"')
            out.extend(f"{indent}    {bl}" for bl in body)
        elif kind in _ADMONITION_KINDS:
            out.append(f"{indent}!!! {kind}")
            out.extend(f"{indent}    {bl}" for bl in body)
        else:
            # Unknown directive — leave alone.
            out.append(line)
            i += 1
            continue

        out.append("")
        i = j

    return "\n".join(out)


def prepare_docstring(doc: str | None) -> str:
    """Dedent and RST→MD convert a raw ``__doc__`` string. Empty string if None."""
    if not doc:
        return ""
    return rst_to_md_docstring(cleandoc(doc))


def including_sub_modules(module: ModuleType) -> Generator[ModuleType, None, None]:
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
