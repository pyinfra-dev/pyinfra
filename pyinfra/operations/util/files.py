import re
from datetime import datetime

from pyinfra.api import QuoteString, StringCommand


def unix_path_join(*parts):
    parts = list(parts)
    parts[0:-1] = [part.rstrip("/") for part in parts[0:-1]]
    return "/".join(parts)


def ensure_mode_int(mode):
    # Already an int (/None)?
    if isinstance(mode, int) or mode is None:
        return mode

    try:
        # Try making an int ('700' -> 700)
        return int(mode)

    except (TypeError, ValueError):
        pass

    # Return as-is (ie +x which we don't need to normalise, it always gets run)
    return mode


def get_timestamp():
    return datetime.now().strftime("%y%m%d%H%M")


def sed_replace(
    filename,
    line,
    replace,
    flags=None,
    backup=False,
    interpolate_variables=False,
):
    flags = "".join(flags) if flags else ""

    line = line.replace("/", r"\/")
    replace = str(replace)
    replace = replace.replace("/", r"\/")
    replace = replace.replace("&", r"\&")
    backup_extension = get_timestamp()

    if interpolate_variables:
        line = line.replace('"', '\\"')
        replace = replace.replace('"', '\\"')
        sed_script_formatter = '"s/{0}/{1}/{2}"'
    else:
        # Single quotes cannot contain other single quotes, even when escaped , so turn
        # each ' into '"'"' (end string, double quote the single quote, (re)start string)
        line = line.replace("'", "'\"'\"'")
        replace = replace.replace("'", "'\"'\"'")
        sed_script_formatter = "'s/{0}/{1}/{2}'"

    sed_script = sed_script_formatter.format(line, replace, flags)

    sed_command = StringCommand(
        "sed",
        "-i.{0}".format(backup_extension),
        sed_script,
        QuoteString(filename),
    )

    if not backup:  # if we're not backing up, remove the file *if* sed succeeds
        backup_filename = "{0}.{1}".format(filename, backup_extension)
        sed_command = StringCommand(sed_command, "&&", "rm", "-f", QuoteString(backup_filename))

    return sed_command


def chmod(target, mode, recursive=False):
    args = ["chmod"]
    if recursive:
        args.append("-R")

    args.append("{0}".format(mode))

    return StringCommand(" ".join(args), QuoteString(target))


def chown(target, user, group=None, recursive=False, dereference=True):
    command = "chown"
    user_group = None

    if user and group:
        user_group = "{0}:{1}".format(user, group)

    elif user:
        user_group = user

    elif group:
        command = "chgrp"
        user_group = group

    args = [command]
    if recursive:
        args.append("-R")

    if not dereference:
        args.append("-h")

    return StringCommand(" ".join(args), user_group, QuoteString(target))


def adjust_regex(line, escape_regex_characters):
    """
    Ensure the regex starts with '^' and ends with '$' and escape regex characters if requested
    """
    match_line = line

    if escape_regex_characters:
        match_line = re.sub(r"([\.\\\+\*\?\[\^\]\$\(\)\{\}\-])", r"\\\1", match_line)

    # Ensure we're matching a whole line, note: match may be a partial line so we
    # put any matches on either side.
    if not match_line.startswith("^"):
        match_line = "^.*{0}".format(match_line)
    if not match_line.endswith("$"):
        match_line = "{0}.*$".format(match_line)

    return match_line
