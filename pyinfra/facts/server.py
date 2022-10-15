import os
import re
import shutil
from datetime import datetime
from tempfile import mkdtemp

from dateutil.parser import parse as parse_date

from pyinfra.api import FactBase, ShortFactBase
from pyinfra.api.util import try_int

from .util.distro import get_distro_info

ISO_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"


class User(FactBase):
    """
    Returns the name of the current user.
    """

    command = "echo $USER"


class Home(FactBase):
    """
    Returns the home directory of the current user.
    """

    command = "echo $HOME"


class Path(FactBase):
    """
    Returns the path environment variable of the current user.
    """

    command = "echo $PATH"


class Hostname(FactBase):
    """
    Returns the current hostname of the server.
    """

    command = "uname -n"


class Kernel(FactBase):
    """
    Returns the kernel name according to ``uname``.
    """

    command = "uname -s"


class KernelVersion(FactBase):
    """
    Returns the kernel version according to ``uname``.
    """

    command = "uname -r"


# Deprecated/renamed -> Kernel
class Os(FactBase):
    """
    Returns the OS name according to ``uname``.

    .. warning::
        This fact is deprecated/renamed, please use the ``server.Kernel`` fact.
    """

    command = "uname -s"


# Deprecated/renamed -> KernelVersion
class OsVersion(FactBase):
    """
    Returns the OS version according to ``uname``.

    .. warning::
        This fact is deprecated/renamed, please use the ``server.KernelVersion`` fact.
    """

    command = "uname -r"


class Arch(FactBase):
    """
    Returns the system architecture according to ``uname``.
    """

    # ``uname -p`` is not portable and returns ``unknown`` on Debian.
    # ``uname -m`` works on most Linux and BSD systems.
    command = "uname -m"


class Command(FactBase):
    """
    Returns the raw output lines of a given command.
    """

    @staticmethod
    def command(command):
        return command


class Which(FactBase):
    """
    Returns the path of a given command, if available.
    """

    @staticmethod
    def command(command):
        return "which {0} || true".format(command)


class Date(FactBase):
    """
    Returns the current datetime on the server.
    """

    command = f"date +'{ISO_DATE_FORMAT}'"
    default = datetime.now

    @staticmethod
    def process(output):
        return datetime.strptime(output[0], ISO_DATE_FORMAT)


class MacosVersion(FactBase):
    """
    Returns the installed MacOS version.
    """

    command = "sw_vers -productVersion"
    requires_command = "sw_vers"


class Mounts(FactBase):
    """
    Returns a dictionary of mounted filesystems and information.

    .. code:: python

        {
            "/": {
                "device": "/dev/mv2",
                "type": "ext4",
                "options": [
                    "rw",
                    "relatime"
                ]
            },
        }
    """

    command = "mount"
    default = dict

    @staticmethod
    def process(output):
        devices = {}

        for line in output:
            is_map = False
            if line.startswith("map "):
                line = line[4:]
                is_map = True

            device, _, path, other_bits = line.split(" ", 3)

            if is_map:
                device = "map {0}".format(device)

            if other_bits.startswith("type"):
                _, type_, options = other_bits.split(" ", 2)
                options = options.strip("()").split(",")
            else:
                options = other_bits.strip("()").split(",")
                type_ = options.pop(0)

            devices[path] = {
                "device": device,
                "type": type_,
                "options": [option.strip() for option in options],
            }

        return devices


class KernelModules(FactBase):
    """
    Returns a dictionary of kernel module name -> info.

    .. code:: python

        {
            "module_name": {
                "size": 0,
                "instances": 0,
                "state": "Live",
            },
        }
    """

    command = "! test -f /proc/modules || cat /proc/modules"
    default = dict

    @staticmethod
    def process(output):
        modules = {}

        for line in output:
            name, size, instances, depends, state, _ = line.split(" ", 5)
            instances = int(instances)

            module = {
                "size": size,
                "instances": instances,
                "state": state,
            }

            if depends != "-":
                module["depends"] = [value for value in depends.split(",") if value]

            modules[name] = module

        return modules


class LsbRelease(FactBase):
    """
    Returns a dictionary of release information using ``lsb_release``.

    .. code:: python

        {
            "id": "Ubuntu",
            "description": "Ubuntu 18.04.2 LTS",
            "release": "18.04",
            "codename": "bionic",
            ...
        }
    """

    command = "lsb_release -ca"
    requires_command = "lsb_release"

    @staticmethod
    def process(output):
        items = {}

        for line in output:
            if ":" not in line:
                continue

            key, value = line.split(":", 1)

            key = key.strip().lower()

            # Turn "distributor id" into "id"
            if " " in key:
                key = key.split(" ")[-1]

            value = value.strip()

            items[key] = value

        return items


class Sysctl(FactBase):
    """
    Returns a dictionary of sysctl settings and values.

    .. code:: python

        {
            "fs.inotify.max_queued_events": 16384,
            "fs.inode-state": [
                44565,
                360,
            ],
        }
    """

    command = "sysctl -a"
    default = dict

    @staticmethod
    def process(output):
        sysctls = {}

        for line in output:
            key = values = None

            if "=" in line:
                key, values = line.split("=", 1)
            elif ":" in line:
                key, values = line.split(":", 1)
            else:
                continue  # pragma: no cover

            if key and values:
                key = key.strip()
                values = values.strip()

                if re.match(r"^[a-zA-Z0-9_\.\s]+$", values):
                    values = [try_int(item.strip()) for item in values.split()]

                    if len(values) == 1:
                        values = values[0]

                sysctls[key] = values

        return sysctls


class Groups(FactBase):
    """
    Returns a list of groups on the system.
    """

    command = "cat /etc/group"
    default = list

    @staticmethod
    def process(output):
        groups = []

        for line in output:
            if ":" in line:
                groups.append(line.split(":")[0])

        return groups


class Crontab(FactBase):
    """
    Returns a dictionary of cron command -> execution time.

    .. code:: python

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
    """

    default = dict

    requires_command = "crontab"

    @staticmethod
    def command(user=None):
        if user:
            return "crontab -l -u {0} || true".format(user)
        return "crontab -l || true"

    @staticmethod
    def process(output):
        crons = {}
        current_comments = []

        for line in output:
            line = line.strip()
            if not line or line.startswith("#"):
                current_comments.append(line)
                continue

            if line.startswith("@"):
                special_time, command = line.split(None, 1)
                crons[command] = {
                    "special_time": special_time,
                    "comments": current_comments,
                }
            else:
                minute, hour, day_of_month, month, day_of_week, command = line.split(None, 5)
                crons[command] = {
                    "minute": try_int(minute),
                    "hour": try_int(hour),
                    "month": try_int(month),
                    "day_of_month": try_int(day_of_month),
                    "day_of_week": try_int(day_of_week),
                    "comments": current_comments,
                }

            current_comments = []
        return crons


class Users(FactBase):
    """
    Returns a dictionary of users -> details.

    .. code:: python

        {
            "user_name": {
                "comment": "Full Name",
                "home": "/home/user_name",
                "shell": "/bin/bash,
                "group": "main_user_group",
                "groups": [
                    "other",
                    "groups"
                ],
                "uid": user_id,
                "gid": main_user_group_id,
                "lastlog": last_login_time,
            },
        }
    """

    command = """
        for i in `cat /etc/passwd | cut -d: -f1`; do
            ENTRY=`grep ^$i: /etc/passwd`;
            LASTLOG=`lastlog -u $i | grep ^$i` | tr -s ' ';
            echo "$ENTRY|`id -gn $i`|`id -Gn $i`|$LASTLOG";
        done
    """.strip()

    default = dict

    def process(self, output):
        users = {}
        rex = r"[A-Z][a-z]{2} [A-Z][a-z]{2} {1,2}\d+ .+$"

        for line in output:
            entry, group, user_groups, lastlog = line.split("|")

            if entry:
                # Parse out the comment/home/shell
                entries = entry.split(":")

                # Parse groups
                groups = []
                for group_name in user_groups.split(" "):
                    # We only want secondary groups here
                    if group_name and group_name != group:
                        groups.append(group_name)

                raw_login_time = None
                login_time = None

                # Parse lastlog info
                # lastlog output varies, which is why I use regex to match login time
                login = re.search(rex, lastlog)
                if login:
                    raw_login_time = login.group()
                    login_time = parse_date(raw_login_time)

                users[entries[0]] = {
                    "home": entries[5] or None,
                    "comment": entries[4] or None,
                    "shell": entries[6] or None,
                    "group": group,
                    "groups": groups,
                    "uid": int(entries[2]),
                    "gid": int(entries[3]),
                    "lastlog": raw_login_time,
                    "login_time": login_time,
                }

        return users


class LinuxDistribution(FactBase):
    """
    Returns a dict of the Linux distribution version. Ubuntu, Debian, CentOS,
    Fedora & Gentoo currently. Also contains any key/value items located in
    release files.

    .. code:: python

        {
            "name": "Ubuntu",
            "major": 20,
            "minor": 04,
            "release_meta": {
                "CODENAME": "focal",
                "ID_LIKE": "debian",
                ...
            }
        }
    """

    command = (
        "cd /etc/ && for file in $(ls -pdL *-release | grep -v /); "
        'do echo "/etc/${file}"; cat "/etc/${file}"; echo ---; '
        "done"
    )

    name_to_pretty_name = {
        "alpine": "Alpine",
        "centos": "CentOS",
        "fedora": "Fedora",
        "gentoo": "Gentoo",
        "opensuse": "openSUSE",
        "rhel": "RedHat",
        "ubuntu": "Ubuntu",
        "debian": "Debian",
    }

    @staticmethod
    def default():
        return {
            "name": None,
            "major": None,
            "minor": None,
            "release_meta": {},
        }

    def process(self, output):
        parts = {}
        for part in "\n".join(output).strip().split("---"):
            if not part.strip():
                continue
            try:
                filename, content = part.strip().split("\n", 1)
                parts[filename] = content
            except ValueError:
                # skip empty files
                # for instance arch linux as an empty file at /etc/arch-release
                continue

        release_info = self.default()
        if not parts:
            return release_info

        temp_root = mkdtemp()
        try:
            temp_etc_dir = os.path.join(temp_root, "etc")
            os.mkdir(temp_etc_dir)

            for filename, content in parts.items():
                with open(os.path.join(temp_etc_dir, os.path.basename(filename)), "w") as fp:
                    fp.write(content)

            parsed = get_distro_info(temp_root)

            release_meta = {key.upper(): value for key, value in parsed.os_release_info().items()}
            # Distro 1.7+ adds this, breaking tests
            # TODO: fix this!
            release_meta.pop("RELEASE_CODENAME", None)

            release_info.update(
                {
                    "name": self.name_to_pretty_name.get(parsed.id(), parsed.name()),
                    "major": try_int(parsed.major_version()) or None,
                    "minor": try_int(parsed.minor_version()) or None,
                    "release_meta": release_meta,
                },
            )

        finally:
            shutil.rmtree(temp_root)

        return release_info


class LinuxName(ShortFactBase):
    """
    Returns the name of the Linux distribution. Shortcut for
    ``host.get_fact(LinuxDistribution)['name']``.
    """

    fact = LinuxDistribution

    @staticmethod
    def process_data(data):
        return data["name"]


class Selinux(FactBase):
    """
    Discovers the SELinux related facts on the target host.

    .. code:: python

        {
            "mode": "enabled",
        }
    """

    command = "sestatus"
    requires_command = "sestatus"

    @staticmethod
    def default():
        return {
            "mode": None,
        }

    def process(self, output):
        selinux_info = self.default()

        match = re.match(r"^SELinux status:\s+(\S+)", "\n".join(output))

        if not match:
            return selinux_info

        selinux_info["mode"] = match.group(1)

        return selinux_info


class LinuxGui(FactBase):
    """
    Returns a list of available Linux GUIs.
    """

    command = "ls /usr/bin/*session || true"
    default = list

    known_gui_binaries = {
        "/usr/bin/gnome-session": "GNOME",
        "/usr/bin/mate-session": "MATE",
        "/usr/bin/lxsession": "LXDE",
        "/usr/bin/plasma_session": "KDE Plasma",
        "/usr/bin/xfce4-session": "XFCE 4",
    }

    def process(self, output):
        gui_names = []

        for line in output:
            gui_name = self.known_gui_binaries.get(line)
            if gui_name:
                gui_names.append(gui_name)

        return gui_names


class HasGui(ShortFactBase):
    """
    Returns a boolean indicating the remote side has GUI capabilities. Linux only.
    """

    fact = LinuxGui

    @staticmethod
    def process_data(data):
        return len(data) > 0
