from __future__ import annotations

from pyinfra import logger
from pyinfra.api.command import QuoteString, StringCommand
from pyinfra.api.operation import operation
from pyinfra.api.util import try_int
from pyinfra.context import host
from pyinfra.facts.crontab import Crontab, CrontabFile
from pyinfra.operations.util.files import sed_delete, sed_replace


@operation()
def crontab(
    command: str,
    present=True,
    user: str | None = None,
    cron_name: str | None = None,
    minute: list[str | int] | str | int | None = None,
    hour: list[str | int] | str | int | None = None,
    month: list[str | int] | str | int | None = None,
    day_of_week: list[str | int] | str | int | None = None,
    day_of_month: list[str | int] | str | int | None = None,
    special_time: str | None = None,
    interpolate_variables=False,
):
    """
    Add/remove/update crontab entries.

    + command: the command for the cron
    + present: whether this cron command should exist
    + user: the user whose crontab to manage
    + cron_name: name the cronjob so future changes to the command will overwrite
    + modify_cron_name: modify the cron name
    + minute: which minutes to execute the cron
    + hour: which hours to execute the cron
    + month: which months to execute the cron
    + day_of_week: which day of the week to execute the cron
    + day_of_month: which day of the month to execute the cron
    + special_time: cron "nickname" time (@reboot, @daily, etc), overrides others
    + interpolate_variables: whether to interpolate variables in ``command``

    Cron commands:
        Unless ``name`` is specified the command is used to identify crontab entries.
        This means commands must be unique within a given users crontab. If you require
        multiple identical commands, provide a different name argument for each.

    Cron schedule:
        The values for ``minute``, ``hour``, ``month``, ``day_of_week``,
        ``day_of_month`` can be specified as an integer, a string containing
        a cron schedule or a list of integers or strings. The effective default
        value of all these arguments is "*" when ``special_time`` is not set.

    Special times:
        When provided, ``special_time`` will be used instead of any values passed in
        for ``minute``/``hour``/``month``/``day_of_week``/``day_of_month``.

    **Examples:**

    .. code:: python

        from pyinfra.operations import crontab

        # simple example for a crontab
        crontab.crontab(
            name="Backup /etc weekly",
            command="/bin/tar cf /tmp/etc_bup.tar /etc",
            cron_name="backup_etc",
            day_of_week=0,
            hour=1,
            minute=0,
        )

        # execute every five minutes
        crontab.crontab(
            name="A harmless monitoring example",
            command="/usr/bin/ping 127.0.0.1",
            minute="*/5"
        )

        # execute on reboot
        crontab.crontab(
            name="Create a directory on reboot",
            command="/usr/bin/mkdir /var/run/my_directory",
            special_time="@reboot"
        )
    """

    def comma_sep(value):
        if isinstance(value, (list, tuple)):
            return ",".join(f"{v}" for v in value)
        return value

    minute = comma_sep(minute)
    hour = comma_sep(hour)
    month = comma_sep(month)
    day_of_week = comma_sep(day_of_week)
    day_of_month = comma_sep(day_of_month)

    ctb0: CrontabFile | dict = host.get_fact(Crontab, user=user)
    # facts from test are in dict
    if isinstance(ctb0, dict):
        ctb = CrontabFile(ctb0)
    else:
        ctb = ctb0
    name_comment = f"# pyinfra-name={cron_name}"

    existing_crontab = ctb.get_command(
        command=command if cron_name is None else None, name=cron_name
    )
    existing_crontab_command = existing_crontab["command"] if existing_crontab else command
    existing_crontab_match = existing_crontab["command"] if existing_crontab else command

    exists = existing_crontab is not None
    exists_name = existing_crontab is not None and name_comment in existing_crontab.get(
        "comments", ""
    )

    edit_commands: list[str | StringCommand] = []
    temp_filename = host.get_temp_filename()

    if special_time:
        new_crontab_line = f"{special_time} {command}"
    else:
        if minute is None:
            minute = "*"
        if hour is None:
            hour = "*"
        if day_of_month is None:
            day_of_month = "*"
        if month is None:
            month = "*"
        if day_of_week is None:
            day_of_week = "*"
        new_crontab_line = f"{minute} {hour} {day_of_month} {month} {day_of_week} {command}"

    existing_crontab_match = f".*{existing_crontab_match}.*"

    # Don't want the cron and it does exist? Remove the line
    if not present and exists:
        edit_commands.append(
            sed_delete(
                temp_filename,
                existing_crontab_match,
                "",
                interpolate_variables=interpolate_variables,
            ),
        )

    # Want the cron but it doesn't exist? Append the line
    elif present and not exists:
        logger.debug(f"present: {present}, exists: {exists}")
        if ctb:  # append a blank line if cron entries already exist
            edit_commands.append(f"echo '' >> {temp_filename}")
        if cron_name:
            edit_commands.append(
                StringCommand("echo", QuoteString(name_comment), ">>", temp_filename),
            )

        edit_commands.append(
            StringCommand("echo", QuoteString(new_crontab_line), ">>", temp_filename),
        )

    # We have the cron and it exists, do it's details? If not, replace the line
    elif present and exists:
        assert existing_crontab is not None
        if any(
            (
                exists_name != (cron_name is not None),
                special_time != existing_crontab.get("special_time"),
                try_int(minute) != existing_crontab.get("minute"),
                try_int(hour) != existing_crontab.get("hour"),
                try_int(month) != existing_crontab.get("month"),
                try_int(day_of_week) != existing_crontab.get("day_of_week"),
                try_int(day_of_month) != existing_crontab.get("day_of_month"),
                existing_crontab_command != command,
            ),
        ):
            if not exists_name and cron_name:
                new_crontab_line = f"{name_comment}\\n{new_crontab_line}"
            edit_commands.append(
                sed_replace(
                    temp_filename,
                    existing_crontab_match,
                    new_crontab_line,
                    interpolate_variables=interpolate_variables,
                ),
            )

    if edit_commands:
        crontab_args = []
        if user:
            crontab_args.append(f"-u {user}")

        # List the crontab into a temporary file if it exists
        if ctb:
            yield f"crontab -l {' '.join(crontab_args)} > {temp_filename}"

        # Now yield any edits
        yield from edit_commands

        # Finally, use the tempfile to write a new crontab
        yield f"crontab {' '.join(crontab_args)} {temp_filename}"
    else:
        host.noop(
            f"crontab {command} {'exists' if present else 'does not exist'}",
        )
