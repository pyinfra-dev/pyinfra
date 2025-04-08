import re
from typing import Dict, List, Optional, TypedDict, Union

from typing_extensions import NotRequired, override

from pyinfra.api import FactBase
from pyinfra.api.util import try_int


class CrontabDict(TypedDict):
    command: NotRequired[str]
    # handles cases like CRON_TZ=UTC
    env: NotRequired[str]
    minute: NotRequired[Union[int, str]]
    hour: NotRequired[Union[int, str]]
    month: NotRequired[Union[int, str]]
    day_of_month: NotRequired[Union[int, str]]
    day_of_week: NotRequired[Union[int, str]]
    comments: NotRequired[List[str]]
    special_time: NotRequired[str]


# for compatibility, also keeps a dict of command -> crontab dict
class CrontabFile:
    commands: List[CrontabDict]

    def __init__(self, input_dict: Optional[Dict[str, CrontabDict]] = None):
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
        self, command: Optional[str] = None, name: Optional[str] = None
    ) -> Optional[CrontabDict]:
        assert command or name, "Either command or name must be provided"

        name_comment = "# pyinfra-name={0}".format(name)
        for cmd in self.commands:
            if cmd.get("command") == command:
                return cmd
            if cmd.get("comments") and name_comment in cmd["comments"]:
                return cmd
        return None

    def get_env(self, env: str) -> Optional[CrontabDict]:
        for cmd in self.commands:
            if cmd.get("env") == env:
                return cmd
        return None

    def get(self, item: str) -> Optional[CrontabDict]:
        return self.get_command(command=item, name=item) or self.get_env(item)

    def __getitem__(self, item) -> Optional[CrontabDict]:
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


_crontab_env_re = re.compile(r"^\s*([A-Z_]+)=(.*)$")


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
               command: "/path/to/command",
               minute: "*",
               hour: "*",
               month: "*",
               day_of_month: "*",
               day_of_week: "*",
            },
            {
                "command": "echo another command
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
            return "crontab -l -u {0} || true".format(user)
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
