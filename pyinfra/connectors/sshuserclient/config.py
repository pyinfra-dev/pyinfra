"""
This file as originally part of the "sshuserclient" pypi package. The GitHub
source has now vanished (https://github.com/tobald/sshuserclient).
"""

import glob
import re
from os import environ, path

import paramiko.config
from gevent.subprocess import CalledProcessError, check_call
from paramiko import SSHConfig as ParamikoSSHConfig

from pyinfra import logger

SETTINGS_REGEX = re.compile(r"(\w+)(?:\s*=\s*|\s+)(.+)")


class FakeInvokeResult:
    ok = False


class FakeInvoke:
    @staticmethod
    def run(cmd, *args, **kwargs):
        result = FakeInvokeResult()

        try:
            cmd = [environ["SHELL"], cmd]
            try:
                code = check_call(cmd)
            except CalledProcessError as e:
                code = e.returncode
            result.ok = code == 0
        except Exception as e:
            logger.warning(
                ("pyinfra encountered an error loading SSH config match exec {0}: {1}").format(
                    cmd,
                    e,
                ),
            )

        return result


paramiko.config.invoke = FakeInvoke  # type: ignore


def _expand_include_statements(file_obj, parsed_files=None):
    parsed_lines = []

    for line in file_obj.readlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        match = re.match(SETTINGS_REGEX, line)
        if not match:
            parsed_lines.append(line)
            continue

        key = match.group(1).lower()
        value = match.group(2)

        if key != "include":
            parsed_lines.append(line)
            continue

        if parsed_files is None:
            parsed_files = []

        # The path can be relative to its parent configuration file
        if path.isabs(value) is False and value[0] != "~":
            folder = path.dirname(file_obj.name)
            value = path.join(folder, value)

        value = path.expanduser(value)

        for filename in glob.iglob(value):
            if path.isfile(filename):
                if filename in parsed_files:
                    raise Exception(
                        "Include loop detected in ssh config file: %s" % filename,
                    )
                with open(filename, encoding="utf-8") as fd:
                    parsed_files.append(filename)
                    parsed_lines.extend(_expand_include_statements(fd, parsed_files))

    return parsed_lines


class SSHConfig(ParamikoSSHConfig):
    """
    an SSHConfig that supports includes directives
    https://github.com/paramiko/paramiko/pull/1194
    """

    def parse(self, file_obj):
        file_obj = _expand_include_statements(file_obj)
        return super().parse(file_obj)
