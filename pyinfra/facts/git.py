from __future__ import annotations

import re

from typing_extensions import override

from pyinfra.api.facts import FactBase


class GitFactBase(FactBase):
    @override
    def requires_command(self, *args, **kwargs) -> str:
        return "git"


class GitBranch(GitFactBase):
    @override
    def command(self, repo) -> str:
        return "! test -d {0} || (cd {0} && git describe --all)".format(repo)

    @override
    def process(self, output):
        return re.sub(r"(heads|tags)/", r"", "\n".join(output))


class GitTag(GitFactBase):
    @override
    def command(self, repo) -> str:
        return "! test -d {0} || (cd {0} && git tag)".format(repo)

    @override
    def process(self, output):
        return output


class GitConfig(GitFactBase):
    default = dict

    @override
    def command(self, repo=None, system=False) -> str:
        if repo is None:
            level = "--system" if system else "--global"
            return f"git config {level} -l || true"

        return "! test -d {0} || (cd {0} && git config --local -l)".format(repo)

    @override
    def process(self, output):
        items: dict[str, list[str]] = {}

        for line in output:
            key, value = line.split("=", 1)
            items.setdefault(key, []).append(value)

        return items


class GitTrackingBranch(GitFactBase):
    @override
    def command(self, repo) -> str:
        return r"! test -d {0} || (cd {0} && git status --branch --porcelain)".format(repo)

    @override
    def process(self, output):
        if not output:
            return None

        m = re.search(r"\.{3}(\S+)\b", list(output)[0])
        if m:
            return m.group(1)
        return None
