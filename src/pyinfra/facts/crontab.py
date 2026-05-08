import re
from typing import TypedDict

from typing_extensions import NotRequired, override

from pyinfra.api import FactBase
from pyinfra.api.util import try_int


class CrontabDict(TypedDict):
    command: NotRequired[str]
    # handles cases like CRON_TZ=UTC
    env: NotRequired[str]
    minute: NotRequired[int | str]
    hour: NotRequired[int | str]
    month: NotRequired[int | str]
    day_of_month: NotRequired[int | str]
    day_of_week: NotRequired[int | str]
    comments: NotRequired[list[str]]
    special_time: NotRequired[str]


# for compatibility, also keeps a dict of command -> crontab dict
class CrontabFile:
    commands: list[CrontabDict]

    def __init__(self, input_dict: dict[str, CrontabDict] | None = None):
        super().__init__()
        self.commands = []
        if input_dict:
            for command, others in input_dict.items():
                val = others.copy()
                val["command"] = command
                self.add_item(val)

    def add_item(self, item: CrontabDict):
        self.commands.append(item)

    def __len__(self):
        return len(self.commands)

    def __bool__(self):
        return len(self) > 0

    def items(self):
        return {item.get("command") or item.get("env"): item for item in self.commands}

    def get_command(
        self, command: str | None = None, name: str | None = None
    ) -> CrontabDict | None:
        assert command or name, "Either command or name must be provided"

        name_comment = f"# pyinfra-name={name}"
        for cmd in self.commands:
            if "command" not in cmd:
                continue
            if cmd.get("command") == command:
                return cmd
            if name_comment in cmd.get("comments", []):
                return cmd
        return None

    def get_env(self, env: str) -> CrontabDict | None:
        for cmd in self.commands:
            if cmd.get("env") == env:
                return cmd
        return None

    def get(self, item: str) -> CrontabDict | None:
        return self.get_command(command=item, name=item) or self.get_env(item)

    def __getitem__(self, item) -> CrontabDict | None:
        return self.get(item)

    @override
    def __repr__(self):
        return f"CrontabResult({self.commands})"

    # noinspection PyMethodMayBeStatic
    def format_item(self, item: CrontabDict):
        lines = []
        for comment in item.get("comments", []):
            lines.append(comment)

        if "env" in item:
            lines.append(item["env"])
        elif "special_time" in item:
            lines.append(f"{item['special_time']} {item['command']}")
        else:
            lines.append(
                f"{item['minute']} {item['hour']} "
                f"{item['day_of_month']} {item['month']} {item['day_of_week']} "
                f"{item['command']}"
            )
        return "\n".join(lines)

    @override
    def __str__(self):
        return "\n".join(self.format_item(item) for item in self.commands)

    def to_json(self):
        return self.commands


# crontab(5) env line: ``name = value`` with optional spaces around ``=``. The
# name may be a bare identifier or placed in matching single/double quotes; the
# value runs to end-of-line (the caller handles any quoting in the value).
_crontab_env_re = re.compile(
    r"""
    ^\s*
    (?:
        "[^"]*"                         # "quoted name"
      | '[^']*'                         # 'quoted name'
      | [A-Za-z_][A-Za-z0-9_]*          # bare identifier
    )
    \s*=
    """,
    re.VERBOSE,
)


class Crontab(FactBase[CrontabFile]):
    """
    Returns a dictionary of CrontabFile.

    .. code:: python

        # CrontabFile.items()
        {
            "/path/to/command": {
                "minute": "*",
                "hour": "*",
                "month": "*",
                "day_of_month": "*",
                "day_of_week": "*",
            },
            "echo another command": {
                "special_time": "@daily",
            },
        }
        # or CrontabFile.to_json()
        [
            {
                "command": "/path/to/command",
                "minute": "*",
                "hour": "*",
                "month": "*",
                "day_of_month": "*",
                "day_of_week": "*",
            },
            {
                "command": "echo another command",
                "special_time": "@daily",
            }
        ]
    """

    default = CrontabFile

    @override
    def requires_command(self, user=None) -> str:
        return "crontab"

    @override
    def command(self, user=None):
        if user:
            return f"crontab -l -u {user} || true"
        return "crontab -l || true"

    @override
    def process(self, output):
        crons = CrontabFile()
        current_comments = []

        for line in output:
            line = line.strip()
            if not line or line.startswith("#"):
                current_comments.append(line)
                continue

            if line.startswith("@"):
                special_time, command = line.split(None, 1)
                item = CrontabDict(
                    command=command,
                    special_time=special_time,
                    comments=current_comments,
                )
                crons.add_item(item)

            elif _crontab_env_re.match(line):
                # handle environment variables
                item = CrontabDict(
                    env=line,
                    comments=current_comments,
                )
                crons.add_item(item)
            else:
                minute, hour, day_of_month, month, day_of_week, command = line.split(None, 5)
                item = CrontabDict(
                    command=command,
                    minute=try_int(minute),
                    hour=try_int(hour),
                    month=try_int(month),
                    day_of_month=try_int(day_of_month),
                    day_of_week=try_int(day_of_week),
                    comments=current_comments,
                )
                crons.add_item(item)

            current_comments = []
        return crons
