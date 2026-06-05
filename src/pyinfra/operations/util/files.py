from __future__ import annotations

import difflib
import re
from datetime import datetime, timezone
from enum import Enum
from collections.abc import Callable, Generator

from pyinfra.api import OperationError, QuoteString, StringCommand
from pyinfra.api.output import format_text


class MetadataTimeField(Enum):
    ATIME = "atime"
    MTIME = "mtime"


def unix_path_join(*parts) -> str:
    part_list = list(parts)
    part_list[0:-1] = [part.rstrip("/") for part in part_list[0:-1]]
    return "/".join(part_list)


def ensure_mode_int(mode: str | int | None) -> int | str | None:
    """
    Normalise the accepted mode spellings to the canonical octal-digit
    integer pyinfra passes to ``chmod`` (and that facts emit), so ``644``,
    ``"644"``, ``"0644"`` and ``"0o644"`` all mean ``rw-r--r--``.

    Integers are read as their octal digit representation (``644`` means
    ``rw-r--r--``), matching the existing operations/facts contract. A true
    octal literal (``0o644``) is indistinguishable from its decimal value
    (``420``) at runtime - use the ``"0o644"`` string form instead.

    Symbolic modes (``"u+x"``) and ``None`` pass through unchanged.
    """
    if mode is None or isinstance(mode, bool):
        return mode

    if isinstance(mode, int):
        digits = str(mode)
    else:
        digits = mode.strip().lower()
        if digits.startswith("0o"):
            digits = digits[2:]
        if not digits.isdigit():
            # Return as-is (ie +x which we don't need to normalise, it always gets run)
            return mode

    if any(c not in "01234567" for c in digits):
        raise ValueError(
            f"Invalid file mode: {mode!r} contains non-octal digits "
            "(expected octal digits 0-7, eg 644, '0644' or '0o644')",
        )

    # Drop any leading zeros ('0644' -> 644) for the canonical digit int
    return int(digits)


def get_timestamp() -> str:
    return datetime.now().strftime("%y%m%d%H%M")


_sed_ignore_case = re.compile("[iI]")


def _sed_delete_builder(line: str, replace: str, flags: str, interpolate_variables: bool) -> str:
    return (
        '"/{0}/{1}d"'
        if interpolate_variables
        # fmt: skip
        else "'/{0}/{1}d'"
    ).format(line, "I" if _sed_ignore_case.search(flags) else "")


def sed_delete(
    filename: str,
    line: str,
    replace: str,
    flags: list[str] | None = None,
    backup=False,
    interpolate_variables=False,
    extended_regex=False,
) -> StringCommand:
    return _sed_command(**locals(), sed_script_builder=_sed_delete_builder)


def _sed_replace_builder(line: str, replace: str, flags: str, interpolate_variables: bool) -> str:
    return (
        '"s/{0}/{1}/{2}"'
        if interpolate_variables
        # fmt: skip
        else "'s/{0}/{1}/{2}'"
    ).format(line, replace, flags)


def sed_replace(
    filename: str,
    line: str,
    replace: str,
    flags: list[str] | None = None,
    backup=False,
    interpolate_variables=False,
    extended_regex=False,
) -> StringCommand:
    return _sed_command(**locals(), sed_script_builder=_sed_replace_builder)


def _sed_command(
    filename: str,
    line: str,
    replace: str,
    flags: list[str] | None = None,
    backup=False,
    interpolate_variables=False,
    extended_regex=False,
    # Python requires a default value here, so use _sed_replace_builder for
    # backwards compatibility.
    sed_script_builder: Callable[[str, str, str, bool], str] = _sed_replace_builder,
) -> StringCommand:
    flags_str = "".join(flags) if flags else ""

    line = line.replace("/", r"\/")
    replace = str(replace)
    replace = replace.replace("/", r"\/")
    replace = replace.replace("&", r"\&")
    backup_extension = get_timestamp()

    if interpolate_variables:
        line = line.replace('"', '\\"')
        replace = replace.replace('"', '\\"')
    else:
        # Single quotes cannot contain other single quotes, even when escaped , so turn
        # each ' into '"'"' (end string, double quote the single quote, (re)start string)
        line = line.replace("'", "'\"'\"'")
        replace = replace.replace("'", "'\"'\"'")

    sed_script = sed_script_builder(line, replace, flags_str, interpolate_variables)

    sed_args: list[str] = ["sed"]
    if extended_regex:
        sed_args.append("-E")
    sed_args.append(f"-i.{backup_extension}")

    sed_command = StringCommand(
        *sed_args,
        sed_script,
        QuoteString(filename),
    )

    if not backup:  # if we're not backing up, remove the file *if* sed succeeds
        backup_filename = f"{filename}.{backup_extension}"
        sed_command = StringCommand(sed_command, "&&", "rm", "-f", QuoteString(backup_filename))

    return sed_command


def chmod(target: str, mode: str | int, recursive=False) -> StringCommand:
    args = ["chmod"]
    if recursive:
        args.append("-R")

    args.append(f"{mode}")

    return StringCommand(" ".join(args), QuoteString(target))


def chown(
    target: str,
    user: str | None = None,
    group: str | None = None,
    recursive=False,
    dereference=True,
) -> StringCommand:
    command = "chown"
    user_group: str | None = None

    if user and group:
        user_group = f"{user}:{group}"

    elif user:
        user_group = user

    elif group:
        command = "chgrp"
        user_group = group

    if user_group is None:
        raise OperationError("chown() requires at least one of user or group")

    args = [command]
    if recursive:
        args.append("-R")

    if not dereference:
        args.append("-h")

    return StringCommand(" ".join(args), QuoteString(user_group), QuoteString(target))


# like the touch command, but only supports setting one field at a time, and expects any
#   reference times to have been read from the reference file metadata and turned into
#   aware datetimes
def touch(
    target: str,
    timefield: MetadataTimeField,
    timesrc: datetime,
    dereference=True,
) -> StringCommand:
    args = ["touch"]

    if timefield is MetadataTimeField.ATIME:
        args.append("-a")
    else:
        args.append("-m")

    if not dereference:
        args.append("-h")

    # don't reinvent the wheel; use isoformat()
    timestr = timesrc.astimezone(timezone.utc).isoformat()
    # but replace the ISO format TZ offset with "Z" for BSD
    timestr = timestr.replace("+00:00", "Z")
    args.extend(["-d", timestr])

    return StringCommand(" ".join(args), QuoteString(target))


def adjust_regex(line: str, escape_regex_characters: bool) -> str:
    """
    Ensure the regex starts with '^' and ends with '$' and escape regex characters if requested
    """
    match_line = line

    if escape_regex_characters:
        match_line = re.sub(r"([\.\\\+\*\?\[\^\]\$\(\)\{\}\-])", r"\\\1", match_line)

    # Ensure we're matching a whole line, note: match may be a partial line so we
    # put any matches on either side.
    if not match_line.startswith("^"):
        match_line = f"^.*{match_line}"
    if not match_line.endswith("$"):
        match_line = f"{match_line}.*$"

    return match_line


def generate_color_diff(
    current_lines: list[str], desired_lines: list[str]
) -> Generator[str, None, None]:
    def _format_range_unified(start: int, stop: int) -> str:
        beginning = start + 1  # lines start numbering with one
        length = stop - start
        if length == 1:
            return f"{beginning}"
        if not length:
            beginning -= 1  # empty ranges begin at line just before the range
        return f"{beginning},{length}"

    for group in difflib.SequenceMatcher(None, current_lines, desired_lines).get_grouped_opcodes(2):
        first, last = group[0], group[-1]
        file1_range = _format_range_unified(first[1], last[2])
        file2_range = _format_range_unified(first[3], last[4])
        yield f"@@ -{file1_range} +{file2_range} @@"

        for tag, i1, i2, j1, j2 in group:
            if tag == "equal":
                for line in current_lines[i1:i2]:
                    yield "  " + line.rstrip()
                continue
            if tag in {"replace", "delete"}:
                for line in current_lines[i1:i2]:
                    yield format_text("- " + line.rstrip(), "red")
            if tag in {"replace", "insert"}:
                for line in desired_lines[j1:j2]:
                    yield format_text("+ " + line.rstrip(), "green")
