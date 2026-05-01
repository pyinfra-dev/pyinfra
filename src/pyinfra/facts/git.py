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


_SHA_RE = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")


class GitLocalCommit(GitFactBase):
    """
    Returns the SHA of ``ref`` (defaults to ``HEAD``) in a local git repository,
    or ``None`` when the repository does not exist, the ref is unknown, or the
    command fails.
    """

    @override
    def command(self, repo: str, ref: str = "HEAD") -> str:
        return "! test -d {0} || (cd {0} && git rev-parse {1} 2>/dev/null)".format(repo, ref)

    @override
    def process(self, output: list[str]):
        if not output:
            return None
        line = output[0].strip()
        return line if _SHA_RE.fullmatch(line) else None


class GitRemoteBranchCommit(GitFactBase):
    """
    Returns the SHA of the tip of ``branch`` on ``remote`` as reported by
    ``git ls-remote``. Returns ``None`` when the remote is unreachable, the
    branch does not exist on the remote, or the repository is missing.
    """

    @override
    def command(self, repo: str, remote: str = "origin", branch: str | None = None) -> str:
        ref = branch if branch else "HEAD"
        return ("! test -d {0} || (cd {0} && git ls-remote {1} {2} 2>/dev/null | head -n1)").format(
            repo, remote, ref
        )

    @override
    def process(self, output: list[str]):
        if not output:
            return None
        parts = output[0].strip().split("\t", 1)
        if parts and _SHA_RE.fullmatch(parts[0]):
            return parts[0]
        return None
