import re

from pyinfra.api.facts import FactBase


class GitBranch(FactBase):
    requires_command = "git"

    @staticmethod
    def command(repo):
        return "! test -d {0} || (cd {0} && git describe --all)".format(repo)

    @staticmethod
    def process(output):
        return re.sub(r"(heads|tags)/", r"", "\n".join(output))


class GitConfig(FactBase):
    default = dict

    requires_command = "git"

    @staticmethod
    def command(repo=None):
        if repo is None:
            return "git config --global -l || true"

        return "! test -d {0} || (cd {0} && git config --local -l)".format(repo)

    @staticmethod
    def process(output):
        items = {}

        for line in output:
            key, value = line.split("=", 1)
            items.setdefault(key, []).append(value)

        return items


class GitTrackingBranch(FactBase):
    requires_command = "git"

    @staticmethod
    def command(repo):
        return r"! test -d {0} || (cd {0} && git status --branch --porcelain)".format(repo)

    @staticmethod
    def process(output):
        if not output:
            return None

        m = re.search(r"\.{3}(\S+)\b", output[0])
        if m:
            return m.group(1)
        return None
