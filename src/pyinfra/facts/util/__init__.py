from collections.abc import Iterable


def make_cat_files_command(*filenames: Iterable[str]) -> str:
    commands = []

    for filename in filenames:
        if "*" in filename:
            # There's no way to test against a glob expression, so accept anything here
            commands.append(f"cat {filename} || true")
        else:
            commands.append(f"! test -f {filename} || cat {filename}")

    if len(commands) > 1:  # if we have multiple, wrap them
        commands = [f"({command})" for command in commands]

    return " && ".join(commands)


def make_cat_files_command_with_markers(marker: str, *filenames: str) -> str:
    """
    Build a shell command that cats each file prefixed by a marker line naming the file.
    Globs are expanded by the shell; missing files (including unexpanded globs) are skipped.
    """

    args = " ".join(filenames)
    return (
        f"for f in {args}; do "
        f'[ -f "$f" ] && {{ printf "{marker} %s\\n" "$f"; cat "$f"; }}; '
        "done || true"
    )
