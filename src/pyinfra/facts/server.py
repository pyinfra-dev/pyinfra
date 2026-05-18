from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime
from tempfile import mkdtemp
from typing import Optional, Union
from collections.abc import Iterable

from dateutil.parser import parse as parse_date
from distro import distro
from typing_extensions import TypedDict, override

from pyinfra import host
from pyinfra.api import FactBase, ShortFactBase, StringCommand
from pyinfra.api.command import QuoteString, make_formatted_string_command
from pyinfra.api.util import try_int
from pyinfra.facts import crontab

ISO_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"


class User(FactBase):
    """
    Returns the name of the current user.
    """

    @override
    def command(self):
        return "echo $USER"


class Home(FactBase[Optional[str]]):
    """
    Returns the home directory of the given user, or the current user if no user is given.
    """

    @override
    def command(self, user=""):
        return f"echo ~{user}"


class Path(FactBase):
    """
    Returns the path environment variable of the current user.
    """

    @override
    def command(self):
        return "echo $PATH"


class TmpDir(FactBase):
    """
    Returns the temporary directory of the current server.

    According to POSIX standards, checks environment variables in this order:
    1. TMPDIR (if set and accessible)
    2. TMP (if set and accessible)
    3. TEMP (if set and accessible)
    4. Falls back to empty string
    """

    @override
    def command(self):
        return """
if [ -n "$TMPDIR" ] && [ -d "$TMPDIR" ] && [ -w "$TMPDIR" ]; then
    echo "$TMPDIR";
elif [ -n "$TMP" ] && [ -d "$TMP" ] && [ -w "$TMP" ]; then
    echo "$TMP";
elif [ -n "$TEMP" ] && [ -d "$TEMP" ] && [ -w "$TEMP" ]; then
    echo "$TEMP";
else
    echo "";
fi
        """.strip()


class Hostname(FactBase):
    """
    Returns the current hostname of the server.
    """

    @override
    def command(self):
        return "uname -n"


class Kernel(FactBase):
    """
    Returns the kernel name according to ``uname``.
    """

    @override
    def command(self):
        return "uname -s"


class KernelVersion(FactBase):
    """
    Returns the kernel version according to ``uname``.
    """

    @override
    def command(self):
        return "uname -r"


class Uptime(FactBase[int]):
    """
    Returns the number of seconds the system has been up.
    """

    @override
    def command(self) -> str:
        self._kernel = host.get_fact(Kernel)
        if self._kernel in ("Darwin", "FreeBSD"):
            return "date +%s; sysctl -n kern.boottime | awk '{print $4}' | tr -d ','"

        return "cut -d. -f1 /proc/uptime"

    @override
    def process(self, output: list[str]) -> int:
        if self._kernel in ("Darwin", "FreeBSD"):
            return int(output[0]) - int(output[1])

        return int(output[0])


# Deprecated/renamed -> Kernel
class Os(FactBase[str]):
    """
    Returns the OS name according to ``uname``.

    .. warning::
        This fact is deprecated/renamed, please use the ``server.Kernel`` fact.
    """

    @override
    def command(self):
        return "uname -s"


# Deprecated/renamed -> KernelVersion
class OsVersion(FactBase[str]):
    """
    Returns the OS version according to ``uname``.

    .. warning::
        This fact is deprecated/renamed, please use the ``server.KernelVersion`` fact.
    """

    @override
    def command(self):
        return "uname -r"


class Arch(FactBase[str]):
    """
    Returns the system architecture according to ``uname``.
    """

    # ``uname -p`` is not portable and returns ``unknown`` on Debian.
    # ``uname -m`` works on most Linux and BSD systems.
    @override
    def command(self):
        return "uname -m"


class Command(FactBase[str]):
    """
    Returns the raw output lines of a given command.
    """

    @override
    def command(self, command):
        return command


class Timezone(FactBase[str]):
    """
    Returns the current system timezone (e.g. ``Europe/Amsterdam``).
    """

    @override
    def command(self) -> str:
        return "readlink -f /etc/localtime | sed 's|.*/zoneinfo/||'"

    @override
    def process(self, output: list[str]) -> str:
        return output[0]


class Which(FactBase[Optional[str]]):
    """
    Returns the path of a given command according to `command -v`, if available.
    """

    @override
    def command(self, command):
        return f"command -v {command} || true"


class Date(FactBase[datetime]):
    """
    Returns the current datetime on the server.
    """

    default = datetime.now

    @override
    def command(self):
        return f"date +'{ISO_DATE_FORMAT}'"

    @override
    def process(self, output) -> datetime:
        return datetime.strptime(list(output)[0], ISO_DATE_FORMAT)


class MacosVersion(FactBase[str]):
    """
    Returns the installed MacOS version.
    """

    @override
    def requires_command(self) -> str:
        return "sw_vers"

    @override
    def command(self):
        return "sw_vers -productVersion"


class ProcessDict(TypedDict):
    user: str
    state: str
    cpu_percent: float
    mem_percent: float
    command: str
    args: str


class MountsDict(TypedDict):
    device: str
    type: str
    options: list[str]


class Mounts(FactBase[dict[str, MountsDict]]):
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

    default = dict

    @override
    def command(self) -> str:
        self._kernel = host.get_fact(Kernel)

        if self._kernel.strip() == "FreeBSD":
            return "mount -p --libxo json"
        else:
            return "cat /proc/self/mountinfo"

    @override
    def process(self, output) -> dict[str, MountsDict]:
        devices: dict[str, MountsDict] = {}

        def unescape_octal(match: re.Match) -> str:
            s = match.group(0)[1:]  # skip the backslash
            return chr(int(s, base=8))

        def replace_octal(s: str) -> str:
            """
            Unescape strings encoded by linux's string_escape_mem with ESCAPE_OCTAL flag.
            """
            return re.sub(r"\\[0-7]{3}", unescape_octal, s)

        if self._kernel == "FreeBSD":
            full_output = "\n".join(output)
            json_output = json.loads(full_output)
            mount_fstab = json_output["mount"]["fstab"]

            for entry in mount_fstab:
                path = entry["mntpoint"]
                type_ = entry["fstype"]
                device = entry["device"]
                options = [option.strip() for option in entry["opts"].split(",")]

                devices[path] = {"device": device, "type": type_, "options": options}

            return devices

        for line in output:
            # ignore mount ID, parent ID, major:minor, root
            _, _, _, _, mount_point, mount_options, line = line.split(sep=" ", maxsplit=6)

            # ignore optional tags "shared", "master", "propagate_from" and "unbindable"
            while True:
                optional, line = line.split(sep=" ", maxsplit=1)
                if optional == "-":
                    break

            fs_type, mount_source, super_options = line.split(sep=" ")

            mount_options = mount_options.split(sep=",")

            # escaped: mount_point, mount_source, super_options
            # these strings can contain characters encoded in octal, e.g. '\054' for ','
            mount_point = replace_octal(mount_point)
            mount_source = replace_octal(mount_source)

            # mount_options will override ro/rw and can be different than the super block options
            # filter them, so they don't appear twice
            super_options = [
                replace_octal(opt)
                for opt in super_options.split(sep=",")
                if opt not in ["ro", "rw"]
            ]

            devices[mount_point] = {
                "device": mount_source,
                "type": fs_type,
                "options": mount_options + super_options,
            }

        return devices


class Port(FactBase[Union[tuple[str, int], tuple[None, None]]]):
    """
    Returns the process occupying a port and its PID.

    Supports TCP and UDP protocols via the ``protocol`` argument (default ``"tcp"``).
    Uses ``ss`` on Linux (with ``netstat`` fallback) and ``sockstat`` on FreeBSD.

    .. code:: python

        # TCP (default)
        host.get_fact(Port, port=80)
        # UDP
        host.get_fact(Port, port=53, protocol="udp")
    """

    @override
    def command(self, port: int, protocol: str = "tcp") -> str:
        self._kernel = host.get_fact(Kernel)

        if self._kernel.strip() == "FreeBSD":
            self._tool = "sockstat"
            return f"sockstat -l -p {port} -P {protocol}"

        # Linux - prefer ss, fall back to netstat
        self._has_ss = host.get_fact(Which, "ss")
        if self._has_ss:
            self._tool = "ss"
            proto_flag = "t" if protocol == "tcp" else "u"
            return f"ss -lp{proto_flag}n | grep ':{port} ' || true"
        else:
            self._tool = "netstat"
            proto_flag = "t" if protocol == "tcp" else "u"
            return f"netstat -{proto_flag}lnp 2>/dev/null | awk '$4 ~ /:{port}$/'"

    @override
    def process(self, output: Iterable[str]) -> tuple[str, int] | tuple[None, None]:
        if self._tool == "ss":
            return self._process_ss(output)
        elif self._tool == "netstat":
            return self._process_netstat(output)
        elif self._tool == "sockstat":
            return self._process_sockstat(output)
        return None, None

    def _process_ss(self, output: Iterable[str]) -> tuple[str, int] | tuple[None, None]:
        for line in output:
            if '"' not in line or "pid=" not in line:
                continue
            proc = line.split('"')[1]
            pid = int(line.split("pid=")[1].split(",")[0])
            return (proc, pid)
        return None, None

    def _process_netstat(self, output: Iterable[str]) -> tuple[str, int] | tuple[None, None]:
        for line in output:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            for part in parts:
                if "/" in part:
                    pid_str, proc = part.split("/", 1)
                    if pid_str.isdigit():
                        return (proc, int(pid_str))
                    break
        return None, None

    def _process_sockstat(self, output: Iterable[str]) -> tuple[str, int] | tuple[None, None]:
        for line in output:
            line = line.strip()
            if not line or line.startswith("USER"):
                continue
            parts = line.split()
            if len(parts) >= 3:
                return (parts[1], int(parts[2]))
        return None, None


class Ports(FactBase[list[dict[str, int | str]]]):
    """
    Returns a list of all listening ports with their processes and PIDs.

    Uses ``ss`` on Linux (with ``netstat`` fallback) and ``sockstat`` on FreeBSD.

    .. code:: python

        host.get_fact(Ports)
    """

    default = list

    @override
    def command(self) -> str:
        self._kernel = host.get_fact(Kernel)

        if self._kernel.strip() == "FreeBSD":
            self._tool = "sockstat"
            return "sockstat -l"
        self._has_ss = host.get_fact(Which, "ss")
        if self._has_ss:
            self._tool = "ss"
            return "ss -lpuntn || true"
        else:
            self._tool = "netstat"
            return "netstat -tunp 2>/dev/null || true"

    @override
    def process(self, output: Iterable[str]) -> list[dict[str, int | str]]:
        if self._tool == "ss":
            return self._process_ss(output)
        elif self._tool == "netstat":
            return self._process_netstat(output)
        elif self._tool == "sockstat":
            return self._process_sockstat(output)
        return []

    def _process_ss(self, output: Iterable[str]) -> list[dict[str, int | str]]:
        results: list[dict[str, int | str]] = []

        for line in output:
            if '"' not in line or "pid=" not in line:
                continue
            parts = line.split('"')
            if len(parts) < 2:
                continue
            proc = parts[1]
            port_info = parts[0].split()
            if len(port_info) < 2:
                continue
            state = port_info[0]
            if state in ("LISTEN", "UNCONN", "ESTAB", "ESTABLISHED"):
                protocol = "udp" if state == "UNCONN" else "tcp"
                addr_idx = 3 if len(port_info) > 3 else 1
            else:
                protocol = "udp" if len(port_info) > 1 and port_info[1] == "UNCONN" else "tcp"
                addr_idx = 4 if len(port_info) > 4 else 1
            if addr_idx < len(port_info):
                addr = port_info[addr_idx]
                if ":" in addr:
                    ip_port = addr.rsplit(":", 1)
                    ip = ip_port[0]
                    if ip.startswith("["):
                        ip = ip[1 : ip.index("]")] if "]" in ip else ip[1:]
                    if "%" in ip:
                        ip = ip.split("%")[0]
                    try:
                        port = int(ip_port[-1])
                    except ValueError:
                        continue
                    results.append({"port": port, "ip": ip, "protocol": protocol, "process": proc})
        return results

    def _process_netstat(self, output: Iterable[str]) -> list[dict[str, int | str]]:
        results: list[dict[str, int | str]] = []
        for line in output:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            protocol = "tcp" if parts[0].startswith("tcp") else "udp"
            for i, part in enumerate(parts):
                if "/" in part:
                    pid_str, proc = part.split("/", 1)
                    if pid_str.isdigit():
                        if i > 0:
                            addr = parts[3]
                            if ":" in addr:
                                ip_port = addr.rsplit(":", 1)
                                ip = ip_port[0]
                                try:
                                    port = int(ip_port[-1])
                                except ValueError:
                                    continue
                                results.append(
                                    {"port": port, "ip": ip, "protocol": protocol, "process": proc}
                                )
                        break
        return results

    def _process_sockstat(self, output: Iterable[str]) -> list[dict[str, int | str]]:
        results: list[dict[str, int | str]] = []
        for line in output:
            line = line.strip()
            if not line or line.startswith("USER"):
                continue
            parts = line.split()
            if len(parts) >= 6:
                try:
                    local_addr = parts[5]
                    ip = "*"
                    port_str = local_addr
                    if ":" in local_addr:
                        ip_port = local_addr.rsplit(":", 1)
                        ip = ip_port[0]
                        port_str = ip_port[-1]
                    elif local_addr.startswith("*."):
                        port_str = local_addr[2:]
                    else:
                        continue
                    port = int(port_str)
                    proc = parts[1]
                    protocol = parts[4]
                    results.append({"port": port, "ip": ip, "protocol": protocol, "process": proc})
                except (ValueError, IndexError):
                    continue
        return results


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

    @override
    def command(self):
        return "! test -f /proc/modules || cat /proc/modules"

    default = dict

    @override
    def process(self, output):
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

    @override
    def command(self):
        return "lsb_release -ca"

    @override
    def requires_command(self):
        return "lsb_release"

    @override
    def process(self, output):
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


class OsRelease(FactBase):
    """
    Returns a dictionary of release information stored in ``/etc/os-release``.

    .. code:: python

        {
          "name": "EndeavourOS",
          "pretty_name": "EndeavourOS",
          "id": "endeavouros",
          "id_like": "arch",
          "build_id": "2024.06.25",
          ...
        }
    """

    @override
    def command(self):
        return "cat /etc/os-release"

    @override
    def process(self, output):
        items = {}

        for line in output:
            if "=" in line:
                key, value = line.split("=", 1)
                items[key.strip().lower()] = value.strip().strip('"')

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

    default = dict

    @override
    def command(self, keys=None):
        if keys is None:
            return "sysctl -a 2>/dev/null || true"
        return f"sysctl {' '.join(keys)} 2>/dev/null || true"

    @override
    def process(self, output):
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

                if re.match(r"^[a-zA-Z0-9_\-\.\s]+$", values):
                    values = [try_int(item.strip()) for item in values.split()]

                    if len(values) == 1:
                        values = values[0]

                sysctls[key] = values

        return sysctls


class Groups(FactBase[list[str]]):
    """
    Returns a list of groups on the system.
    """

    @override
    def command(self):
        return "cat /etc/group"

    default = list

    @override
    def process(self, output) -> list[str]:
        groups: list[str] = []

        for line in output:
            if ":" in line:
                groups.append(line.split(":")[0])

        return groups


# for compatibility
CrontabDict = crontab.CrontabDict
Crontab = crontab.Crontab


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
                "password": encrypted_password,
            },
        }
    """

    @override
    def command(self):
        return """

        for i in `cat /etc/passwd | cut -d: -f1`; do
            ENTRY=`grep ^$i: /etc/passwd`;
            LASTLOG=`(((lastlog -u $i || lastlogin $i) 2> /dev/null) | grep ^$i | tr -s ' ')`;
            PASSWORD=`(grep ^$i: /etc/shadow || grep ^$i: /etc/master.passwd) 2> /dev/null | cut -d: -f2`;
            echo "$ENTRY|`id -gn $i`|`id -Gn $i`|$LASTLOG|$PASSWORD";
        done
    """.strip()  # noqa

    default = dict

    @override
    def process(self, output):
        users = {}
        rex = r"[A-Z][a-z]{2} [A-Z][a-z]{2} {1,2}\d+ .+$"

        for line in output:
            entry, group, user_groups, lastlog, password = line.rsplit("|", 4)

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
                    "password": password,
                }

        return users


class AuthorizedKeys(FactBase[list[str]]):
    """
    Returns the SSH public keys listed in a user's ``~/.ssh/authorized_keys`` file as a
    list of full key strings. Empty lines and lines starting with ``#`` are skipped; the
    file's order is preserved.

    .. code:: python

        [
            "ssh-ed25519 AAAAC3Nz... user@host",
            "ssh-rsa AAAAB3Nz... other@host",
        ]
    """

    default = list

    @override
    def command(self, user: str, path: str | None = None) -> str:
        # Tilde expansion resolves the user's home without another fact round-trip.
        target = path if path is not None else f"~{user}/.ssh/authorized_keys"
        return f"cat {target} 2>/dev/null || true"

    @override
    def process(self, output: Iterable[str]) -> list[str]:
        keys: list[str] = []
        for raw in output:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            keys.append(line)
        return keys


class LinuxDistributionDict(TypedDict):
    name: str | None
    major: int | None
    minor: int | None
    release_meta: dict


class LinuxDistribution(FactBase[LinuxDistributionDict]):
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

    @override
    def command(self) -> str:
        return (
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

    @override
    @staticmethod
    def default() -> LinuxDistributionDict:
        return {
            "name": None,
            "major": None,
            "minor": None,
            "release_meta": {},
        }

    @override
    def process(self, output) -> LinuxDistributionDict:
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
                with open(
                    os.path.join(temp_etc_dir, os.path.basename(filename)),
                    "w",
                    encoding="utf-8",
                ) as fp:
                    fp.write(content)

            parsed = distro.LinuxDistribution(
                root_dir=temp_root,
                include_lsb=False,
                include_uname=False,
            )

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


class LinuxName(ShortFactBase[str]):
    """
    Returns the name of the Linux distribution. Shortcut for
    ``host.get_fact(LinuxDistribution)['name']``.
    """

    fact = LinuxDistribution

    @override
    def process_data(self, data) -> str:
        return data["name"]


class SelinuxDict(TypedDict):
    mode: str | None


class Selinux(FactBase[SelinuxDict]):
    """
    Discovers the SELinux related facts on the target host.

    .. code:: python

        {
            "mode": "enabled",
        }
    """

    @override
    def command(self):
        return "sestatus"

    @override
    def requires_command(self) -> str:
        return "sestatus"

    @override
    @staticmethod
    def default() -> SelinuxDict:
        return {
            "mode": None,
        }

    @override
    def process(self, output) -> SelinuxDict:
        selinux_info = self.default()

        match = re.match(r"^SELinux status:\s+(\S+)", "\n".join(output))

        if not match:
            return selinux_info

        selinux_info["mode"] = match.group(1)

        return selinux_info


class LinuxGui(FactBase[list[str]]):
    """
    Returns a list of available Linux GUIs.
    """

    @override
    def command(self):
        return "ls /usr/bin/*session || true"

    default = list

    known_gui_binaries = {
        "/usr/bin/gnome-session": "GNOME",
        "/usr/bin/mate-session": "MATE",
        "/usr/bin/lxsession": "LXDE",
        "/usr/bin/plasma_session": "KDE Plasma",
        "/usr/bin/xfce4-session": "XFCE 4",
    }

    @override
    def process(self, output) -> list[str]:
        gui_names = []

        for line in output:
            gui_name = self.known_gui_binaries.get(line)
            if gui_name:
                gui_names.append(gui_name)

        return gui_names


class HasGui(ShortFactBase[bool]):
    """
    Returns a boolean indicating the remote side has GUI capabilities. Linux only.
    """

    fact = LinuxGui

    @override
    def process_data(self, data) -> bool:
        return len(data) > 0


class Locales(FactBase[list[str]]):
    """
    Returns installed locales on the target host.

    .. code:: python

        ["C.UTF-8", "en_US.UTF-8"]
    """

    @override
    def command(self) -> str:
        return "locale -a"

    @override
    def requires_command(self) -> str:
        return "locale"

    default = list

    @override
    def process(self, output) -> list[str]:
        # replace utf8 with UTF-8 to match names in /etc/locale.gen
        # return a list of enabled locales
        return [line.replace("utf8", "UTF-8") for line in output]


class SecurityLimits(FactBase):
    """
    Returns a list of security limits on the target host.

    .. code:: python

        [
            {
                "domain": "*",
                "limit_type": "soft",
                "item": "nofile",
                "value": "1048576"
            },
            {
                "domain": "*",
                "limit_type": "hard",
                "item": "nofile",
                "value": "1048576"
            },
            {
                "domain": "root",
                "limit_type": "soft",
                "item": "nofile",
                "value": "1048576"
            },
            {
                "domain": "root",
                "limit_type": "hard",
                "item": "nofile",
                "value": "1048576"
            },
            {
                "domain": "*",
                "limit_type": "soft",
                "item": "memlock",
                "value": "unlimited"
            },
            {
                "domain": "*",
                "limit_type": "hard",
                "item": "memlock",
                "value": "unlimited"
            },
            {
                "domain": "root",
                "limit_type": "soft",
                "item": "memlock",
                "value": "unlimited"
            },
            {
                "domain": "root",
                "limit_type": "hard",
                "item": "memlock",
                "value": "unlimited"
            }
        ]
    """

    @override
    def command(self):
        return "! test -e /etc/security/limits.conf || cat /etc/security/limits.conf"

    default = list

    @override
    def process(self, output):
        limits = []

        for line in output:
            if line.startswith("#") or not len(line.strip()):
                continue

            domain, limit_type, item, value = line.split()

            limits.append(
                {
                    "domain": domain,
                    "limit_type": limit_type,
                    "item": item,
                    "value": value,
                },
            )

        return limits


class RebootRequired(FactBase[bool]):
    """
    Returns a boolean indicating whether the system requires a reboot.

    On Linux systems:

    - Checks /var/run/reboot-required and /var/run/reboot-required.pkgs
    - On Alpine Linux, compares installed kernel with running kernel

    On FreeBSD systems:

    - Compares running kernel version with installed kernel version
    """

    @override
    def command(self) -> str:
        return """
# Get OS type
OS_TYPE=$(uname -s)
if [ "$OS_TYPE" = "Linux" ]; then
    # Check if it's Alpine Linux
    if [ -f /etc/alpine-release ]; then
        RUNNING_KERNEL=$(uname -r)
        INSTALLED_KERNEL=$(ls -1 /lib/modules | sort -V | tail -n1)
        if [ "$RUNNING_KERNEL" != "$INSTALLED_KERNEL" ]; then
            echo "reboot_required"
            exit 0
        fi
    else
        # Check standard Linux reboot required files
        if [ -f /var/run/reboot-required ] || [ -f /var/run/reboot-required.pkgs ]; then
            echo "reboot_required"
            exit 0
        fi
    fi
elif [ "$OS_TYPE" = "FreeBSD" ]; then
    RUNNING_VERSION=$(freebsd-version -r)
    INSTALLED_VERSION=$(freebsd-version -k)
    if [ "$RUNNING_VERSION" != "$INSTALLED_VERSION" ]; then
        echo "reboot_required"
        exit 0
    fi
fi
echo "no_reboot_required"
"""

    @override
    def process(self, output) -> bool:
        return list(output)[0].strip() == "reboot_required"


class Processes(FactBase[dict[int, ProcessDict]]):
    """
    Returns a dictionary of running processes keyed by PID.

    .. code:: python

        {
            1: {
                "user": "root",
                "state": "Ss",
                "cpu_percent": 0.0,
                "mem_percent": 0.1,
                "command": "init",
                "args": "/sbin/init",
            },
        }
    """

    default = dict

    @override
    def command(self, pid: int | None = None) -> str:
        self._kernel = host.get_fact(Kernel)
        is_bsd = self._kernel.strip() in ("FreeBSD", "Darwin")

        # BusyBox ps (Alpine) only supports limited columns.
        # Detect by checking if busybox exists on the system.
        if not is_bsd:
            self._is_busybox = bool(host.get_fact(Which, "busybox"))
        else:
            self._is_busybox = False

        if not self._is_busybox:
            fields = "pid,user,stat,%cpu,%mem,comm,args"
        else:
            # BusyBox ps: only pid, user/uid, vsz, stat, args are reliable
            fields = "pid,user,vsz,stat,args"

        if pid is not None:
            if self._is_busybox:
                return f"LANG=C ps -o {fields} | awk 'NR==1 || $1=={pid}'"
            return f"LANG=C ps -p {pid} -o {fields}"

        if is_bsd:
            return f"LANG=C ps -eo {fields}"
        elif self._is_busybox:
            return f"LANG=C ps -o {fields}"
        else:
            return f"LANG=C ps -eo {fields} --no-headers"

    @override
    def process(self, output: Iterable[str]) -> dict[int, ProcessDict]:
        processes: dict[int, ProcessDict] = {}

        for line in output:
            line = line.strip()
            if not line:
                continue
            if line.startswith("PID"):
                continue

            if not self._is_busybox:
                parts = line.split(None, 6)
                if len(parts) < 6:
                    continue
                try:
                    pid = int(parts[0])
                except ValueError:
                    continue
                args = parts[6] if len(parts) > 6 else parts[5]
                processes[pid] = {
                    "user": parts[1],
                    "state": parts[2],
                    "cpu_percent": float(parts[3]),
                    "mem_percent": float(parts[4]),
                    "command": parts[5],
                    "args": args,
                }
            else:
                # BusyBox format: pid, user, vsz, stat, args
                parts = line.split(None, 4)
                if len(parts) < 5:
                    continue
                try:
                    pid = int(parts[0])
                except ValueError:
                    continue
                args = parts[4]
                command = args.split()[0].rsplit("/", 1)[-1] if args else ""
                processes[pid] = {
                    "user": parts[1],
                    "state": parts[3],
                    "cpu_percent": 0.0,
                    "mem_percent": 0.0,
                    "command": command,
                    "args": args,
                }

        return processes


class EtcHosts(FactBase[dict[str, list[str]]]):
    """
    Returns ``/etc/hosts`` (or the file at ``path``) parsed as a mapping of IP address
    to the list of hostnames declared on the matching lines. Comments and empty lines
    are ignored; when the same IP is listed more than once, hostnames are merged in
    file order.

    .. code:: python

        {
            "127.0.0.1": ["localhost", "localhost.localdomain"],
            "::1": ["localhost"],
            "192.168.1.10": ["db.internal"],
        }
    """

    default = dict

    @override
    def command(self, path: str = "/etc/hosts") -> StringCommand:
        return make_formatted_string_command("cat {0} 2>/dev/null || true", QuoteString(path))

    @override
    def process(self, output: Iterable[str]) -> dict[str, list[str]]:
        entries: dict[str, list[str]] = {}
        for raw in output:
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            ip, hostnames = parts[0], parts[1:]
            existing = entries.setdefault(ip, [])
            for name in hostnames:
                if name not in existing:
                    existing.append(name)
        return entries


class LastRecordDict(TypedDict):
    user: str
    tty: str
    host: str
    time: str


class Last(FactBase[list[LastRecordDict]]):
    """
    Returns login records parsed from ``last`` as a list of dicts.

    Parsing is intentionally light: ``time`` holds the raw trailing string from the
    ``last`` output (e.g. ``"Thu Apr 17 14:00   still logged in"``) so that callers can
    re-parse the date format that matches their system if needed.

    .. code:: python

        [
            {
                "user": "alice",
                "tty": "pts/0",
                "host": "192.168.1.5",
                "time": "Thu Apr 17 14:00   still logged in",
            },
            {
                "user": "reboot",
                "tty": "system boot",
                "host": "6.19.10-arch1-1",
                "time": "Thu Apr 17 11:00 - 12:00  (01:00)",
            },
        ]
    """

    default = list

    _WEEKDAYS = {"Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"}

    @override
    def requires_command(self) -> str:
        return "last"

    @override
    def command(self) -> str:
        # -Fwi (util-linux): full timestamps, wide columns, IPs instead of hostnames.
        # -w alone works on FreeBSD; busybox last rejects all flags, so also fall back
        # to the bare command.
        return "last -Fwi 2>/dev/null || last -w 2>/dev/null || last 2>/dev/null || true"

    @override
    def process(self, output: Iterable[str]) -> list[LastRecordDict]:
        records: list[LastRecordDict] = []
        for raw in output:
            line = raw.rstrip()
            if not line:
                continue

            lower = line.lower()
            if lower.startswith(("wtmp begins", "btmp begins")):
                continue
            # util-linux may emit a "user tty ..." header with -x; skip it
            if lower.startswith(("user ", "username ")):
                continue

            parts = line.split()
            if len(parts) < 3:
                continue

            user = parts[0]
            if user == "reboot" and parts[1] == "system" and parts[2] == "boot":
                tty = "system boot"
                rest = parts[3:]
            else:
                tty = parts[1]
                rest = parts[2:]

            if not rest:
                continue

            if rest[0] in self._WEEKDAYS:
                host = ""
                time_parts = rest
            else:
                host = rest[0]
                time_parts = rest[1:]

            records.append(
                {
                    "user": user,
                    "tty": tty,
                    "host": host,
                    "time": " ".join(time_parts),
                }
            )

        return records


class LoadAverage(FactBase[dict[str, float]]):
    """
    Returns the system load average keyed by window (1, 5 and 15 minutes).

    Reads ``/proc/loadavg`` when available (Linux) and falls back to parsing
    ``uptime`` output on systems without procfs (e.g. FreeBSD).

    .. code:: python

        {
            "1": 0.12,
            "5": 0.21,
            "15": 0.22,
        }
    """

    default = dict

    @override
    def command(self) -> str:
        return "cat /proc/loadavg 2>/dev/null || uptime"

    @override
    def process(self, output: Iterable[str]) -> dict[str, float]:
        for raw in output:
            line = raw.strip()
            if not line:
                continue

            tokens = line.split()
            # /proc/loadavg: "0.00 0.00 0.00 1/145 71536"
            if len(tokens) >= 3:
                try:
                    return {
                        "1": float(tokens[0]),
                        "5": float(tokens[1]),
                        "15": float(tokens[2]),
                    }
                except ValueError:
                    pass

            # uptime: "... load average[s]: 0.12, 0.21, 0.22"
            match = re.search(r"load averages?:\s*([0-9.]+)[,\s]+([0-9.]+)[,\s]+([0-9.]+)", line)
            if match:
                return {
                    "1": float(match.group(1)),
                    "5": float(match.group(2)),
                    "15": float(match.group(3)),
                }

        return {}


class Lastb(Last):
    """
    Returns failed login records parsed from ``lastb`` (``/var/log/btmp``).

    Output shape matches :class:`Last`; see that fact for details. ``lastb`` usually
    requires root to read ``/var/log/btmp``.
    """

    @override
    def requires_command(self) -> str:
        return "lastb"

    @override
    def command(self) -> str:
        # lastb only ships with util-linux; -Fwi matches the Last fact.
        return "lastb -Fwi 2>/dev/null || lastb 2>/dev/null || true"
