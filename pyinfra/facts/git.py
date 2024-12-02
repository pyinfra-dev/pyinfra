from __future__ import annotations

import re

from pyinfra.api.facts import FactBase


class GitFactBase(FactBase):
    def requires_command(self, *args, **kwargs) -> str:
        return "git"


class GitBranch(GitFactBase):
    def command(self, repo) -> str:
        return "! test -d {0} || (cd {0} && git describe --all)".format(repo)

    def process(self, output):
        return re.sub(r"(heads|tags)/", r"", "\n".join(output))


class GitConfig(GitFactBase):
    default = dict

    def command(self, repo=None, system=False) -> str:
        if repo is None:
            level = "--system" if system else "--global"
            return f"git config {level} -l || true"

        return "! test -d {0} || (cd {0} && git config --local -l)".format(repo)

    def process(self, output):
        items: dict[str, list[str]] = {}

        for line in output:
            key, value = line.split("=", 1)
            items.setdefault(key, []).append(value)

        return items


class GitTrackingBranch(GitFactBase):
    def command(self, repo) -> str:
        return r"! test -d {0} || (cd {0} && git status --branch --porcelain)".format(repo)

    def process(self, output):
        if not output:
            return None

        m = re.search(r"\.{3}(\S+)\b", list(output)[0])
        if m:
            return m.group(1)
        return None
