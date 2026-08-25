"""
Manage git repositories and configuration.
"""

from __future__ import annotations

import re

from pyinfra import host
from pyinfra.api import OperationError, QuoteString, StringCommand, operation
from pyinfra.facts.files import Directory, File
from pyinfra.facts.git import (
    GitBranch,
    GitConfig,
    GitLocalCommit,
    GitRemoteBranchCommit,
    GitTag,
    GitTrackingBranch,
)

from . import files, ssh
from .util.files import chown, unix_path_join


@operation()
def config(key: str, value: str, multi_value=False, repo: str | None = None, system=False):
    """
    Manage git config at repository, user or system level.

    + key: the key of the config to ensure
    + value: the value this key should have
    + multi_value: Add the value rather than set it for settings that can have multiple values
    + repo: specify the git repo path to edit local config (defaults to global)
    + system: whether, when ``repo`` is unspecified, to work at system level (or default to global)

    **Examples:**

    .. code:: python

        from pyinfra.operations import git
        git.config(
            name="Always prune specified repo",
            key="fetch.prune",
            value="true",
            repo="/usr/local/src/pyinfra",
        )

        git.config(
            name="Ensure user name is set for all repos of specified user",
            key="user.name",
            value="Anon E. Mouse",
            _sudo=True,
            _sudo_user="anon"
        )

        git.config(
            name="Ensure same date format for all users",
            key="log.date",
            value="iso",
            system=True
        )

    """

    existing_config = {}

    if not repo:
        existing_config = host.get_fact(GitConfig, system=system)

    # Only get the config if the repo exists at this stage
    elif host.get_fact(Directory, path=unix_path_join(repo, ".git")):
        existing_config = host.get_fact(GitConfig, repo=repo)

    if repo is None:
        base_command = StringCommand("git", "config", "--system" if system else "--global")
    else:
        base_command = StringCommand("cd", QuoteString(repo), "&&", "git", "config", "--local")

    quoted_value = StringCommand('"', value, '"', _separator="")

    if not multi_value and existing_config.get(key) != [value]:
        yield StringCommand(base_command, QuoteString(key), quoted_value)

    elif multi_value and value not in existing_config.get(key, []):
        yield StringCommand(base_command, "--add", QuoteString(key), quoted_value)

    else:
        host.noop(f"git config {key} is set to {value}")


@operation()
def repo(
    src: str,
    dest: str,
    branch: str | None = None,
    pull: bool = True,
    rebase: bool = False,
    user: str | None = None,
    group: str | None = None,
    ssh_keyscan: bool = False,
    update_submodules: bool = False,
    recursive_submodules: bool = False,
    depth: int | None = None,
    *,
    fetch_tags: bool = False,
):
    """
    Clone/pull git repositories.

    + src: the git source URL
    + dest: directory to clone to
    + branch: branch to pull/checkout
    + pull: pull any changes for the branch
    + rebase: when pulling, use ``--rebase``
    + user: chown files to this user after
    + group: chown files to this group after
    + ssh_keyscan: keyscan the remote host if not in known_hosts before clone/pull
    + update_submodules: update any git submodules
    + recursive_submodules: update git submodules recursively
    + depth: create a shallow clone with a history truncated to the specified number of commits
    + fetch_tags: Whether all tags should be fetched prior to attempting to check out the specified revision

    **Example:**

    .. code:: python

        git.repo(
            name="Clone repo",
            src="https://github.com/Fizzadar/pyinfra.git",
            dest="/usr/local/src/pyinfra",
        )
    """

    # Ensure our target directory exists
    yield from files.directory._inner(dest)

    # Do we need to scan for the remote host key?
    if ssh_keyscan:
        # Attempt to parse the domain from the git repository
        domain = re.match(r"^[a-zA-Z0-9]+@([0-9a-zA-Z\.\-]+)", src)

        if domain:
            yield from ssh.keyscan._inner(domain.group(1))
        else:
            raise OperationError(
                f"Could not parse domain (to SSH keyscan) from: {src}",
            )

    # Store git commands for directory prefix
    git_commands: list[str | StringCommand] = []
    git_dir = unix_path_join(dest, ".git")
    is_repo = host.get_fact(Directory, path=git_dir)

    # Cloning new repo?
    if not is_repo:
        options: list[str | QuoteString] = []
        if depth is not None:
            options.extend(["--depth", str(depth)])
        if branch:
            options.extend(["--branch", QuoteString(branch)])

        git_commands.append(StringCommand("clone", QuoteString(src), *options, "."))

    # Ensuring existing repo
    else:
        # Reconcile the `origin` remote URL with `src`. If `src` has changed for
        # an existing working copy, update `origin` so the fetch/pull below
        # operate against the new source instead of silently continuing to track
        # the old remote (see GH #1763). Only act when an `origin` URL already
        # exists and differs - if it is missing we leave remote management alone.
        existing_remote = host.get_fact(GitConfig, repo=dest).get("remote.origin.url")
        remote_changed = existing_remote is not None and existing_remote != [src]
        if remote_changed:
            git_commands.append(StringCommand("remote", "set-url", "origin", QuoteString(src)))

        is_tag = False
        current_branch = host.get_fact(GitBranch, repo=dest)
        if branch is not None and current_branch != branch:
            # fetch to ensure we have the branch/tag locally
            if fetch_tags:
                git_commands.append(StringCommand("fetch", "--tags"))
            else:
                git_commands.append(StringCommand("fetch"))

            git_commands.append(StringCommand("checkout", QuoteString(branch)))
        if branch and branch in (host.get_fact(GitTag, repo=dest) or []):
            git_commands.append(StringCommand("checkout", QuoteString(branch)))
            is_tag = True
        if pull and not is_tag:
            skip_pull = False
            # Skip `git pull` when the local branch tip already matches the
            # remote tip, so pyinfra reports the operation unchanged rather
            # than always "Success". This still applies when we switch branch:
            # if the target branch already exists locally at the remote tip,
            # the fetch+checkout leaves nothing for pull to do. When the remote
            # URL just changed, the cached remote-tip fact was gathered against
            # the old origin, so never skip - we must pull from the new source.
            effective_branch = branch or current_branch
            if not remote_changed and effective_branch:
                local_commit = host.get_fact(GitLocalCommit, repo=dest, ref=effective_branch)
                remote_commit = host.get_fact(
                    GitRemoteBranchCommit,
                    repo=dest,
                    branch=effective_branch,
                )
                if local_commit and remote_commit and local_commit == remote_commit:
                    skip_pull = True
            if skip_pull:
                host.noop(
                    f"git repository {dest} is already up to date",
                )
            elif rebase:
                git_commands.append("pull --rebase")
            else:
                git_commands.append("pull")

    if update_submodules:
        if recursive_submodules:
            git_commands.append("submodule update --init --recursive")
        else:
            git_commands.append("submodule update --init")

    # Attach prefixes for directory
    command_prefix = StringCommand("cd", QuoteString(dest), "&&", "git")

    for cmd in git_commands:
        yield StringCommand(command_prefix, cmd)

    # Apply any user or group if we did anything
    if git_commands and (user or group):
        yield chown(dest, user, group, recursive=True)


@operation()
def worktree(
    worktree: str,
    repo: str | None = None,
    detached=False,
    new_branch: str | None = None,
    commitish: str | None = None,
    pull=True,
    rebase=False,
    from_remote_branch: tuple[str, str] | None = None,
    present=True,
    assume_repo_exists=False,
    force=False,
    user: str | None = None,
    group: str | None = None,
):
    """
    Manage git worktrees.

    + worktree: git working tree directory
    + repo: git main repository directory
    + detached: create a working tree with a detached HEAD
    + new_branch: local branch name created at the same time than the worktree
    + commitish: from which git commit, branch, ... the worktree is created
    + pull: pull any changes from a remote branch if set
    + rebase: when pulling, use ``--rebase``
    + from_remote_branch: a 2-tuple ``(remote, branch)`` that identifies a remote branch
    + present: whether the working tree should exist
    + assume_repo_exists: whether to assume the main repo exists
    + force: whether to use ``--force`` when adding/removing worktrees
    + user: chown files to this user after
    + group: chown files to this group after

    **Examples:**

    .. code:: python

        git.worktree(
            name="Create a worktree from the current repo `HEAD`",
            repo="/usr/local/src/pyinfra/master",
            worktree="/usr/local/src/pyinfra/hotfix"
        )

        git.worktree(
            name="Create a worktree from the commit `4e091aa0`",
            repo="/usr/local/src/pyinfra/master",
            worktree="/usr/local/src/pyinfra/hotfix",
            commitish="4e091aa0"
        )

        git.worktree(
            name="Create a worktree from the tag `4e091aa0`, even if already registered",
            repo="/usr/local/src/pyinfra/master",
            worktree="/usr/local/src/pyinfra/2.x",
            commitish="2.x",
            force=True
        )

        git.worktree(
            name="Create a worktree with a new local branch `v1.0`",
            repo="/usr/local/src/pyinfra/master",
            worktree="/usr/local/src/pyinfra/hotfix",
            new_branch="v1.0",
        )

        git.worktree(
            name="Create a worktree from the commit 4e091aa0 with the new local branch `v1.0`",
            repo="/usr/local/src/pyinfra/master",
            worktree="/usr/local/src/pyinfra/hotfix",
            new_branch="v1.0",
            commitish="4e091aa0"
        )

        git.worktree(
            name="Create a worktree with a detached `HEAD`",
            repo="/usr/local/src/pyinfra/master",
            worktree="/usr/local/src/pyinfra/hotfix",
            detached=True,
        )

        git.worktree(
            name="Create a worktree with a detached `HEAD` from commit `4e091aa0`",
            repo="/usr/local/src/pyinfra/master",
            worktree="/usr/local/src/pyinfra/hotfix",
            commitish="4e091aa0",
            detached=True,
        )

        git.worktree(
            name="Create a worktree from the existing local branch `v1.0`",
            repo="/usr/local/src/pyinfra/master",
            worktree="/usr/local/src/pyinfra/hotfix",
            commitish="v1.0"
        )

        git.worktree(
            name="Create a worktree with a new branch `v1.0` that tracks `origin/v1.0`",
            repo="/usr/local/src/pyinfra/master",
            worktree="/usr/local/src/pyinfra/hotfix",
            new_branch="v1.0",
            commitish="v1.0"
        )

        git.worktree(
            name="Idempotent worktree creation, never pulls",
            repo="/usr/local/src/pyinfra/master",
            worktree="/usr/local/src/pyinfra/hotfix",
            new_branch="v1.0",
            commitish="v1.0",
            pull=False
        )

        git.worktree(
            name="Pull an existing worktree already linked to a tracking branch",
            repo="/usr/local/src/pyinfra/master",
            worktree="/usr/local/src/pyinfra/hotfix"
        )

        git.worktree(
            name="Pull an existing worktree from a specific remote branch",
            repo="/usr/local/src/pyinfra/master",
            worktree="/usr/local/src/pyinfra/hotfix",
            from_remote_branch=("origin", "master")
        )

        git.worktree(
            name="Remove a worktree",
            worktree="/usr/local/src/pyinfra/hotfix",
            present=False,
        )

        git.worktree(
            name="Remove an unclean worktree",
            worktree="/usr/local/src/pyinfra/hotfix",
            present=False,
            force=True,
        )
    """

    # Doesn't exist & we want it
    if not host.get_fact(Directory, path=worktree) and present:
        # be sure that `repo` is a GIT repository
        if not assume_repo_exists and not host.get_fact(
            Directory,
            path=unix_path_join(repo, ".git"),
        ):
            raise OperationError(
                f"The following folder is not a valid GIT repository : {repo}",
            )

        if repo is None:
            raise OperationError("repo must be specified when creating a worktree")

        args: list[str | QuoteString] = [
            "cd",
            QuoteString(repo),
            "&&",
            "git",
            "worktree",
            "add",
        ]

        if new_branch:
            args.extend(["-b", QuoteString(new_branch)])
        elif detached:
            args.append("--detach")

        if force:
            args.append("--force")

        args.append(QuoteString(worktree))

        if commitish:
            args.append(QuoteString(commitish))

        yield StringCommand(*args)

        # Apply any user or group
        if user or group:
            yield chown(worktree, user, group, recursive=True)
            # `git worktree add` writes per-worktree metadata under the source
            # repo's `.git/worktrees/<name>/`, plus refs/logs for any new
            # branch it creates. When the command runs as root (e.g. via
            # `_sudo`), those files end up root-owned and break later git
            # commands run as the worktree owner.
            worktree_name = worktree.rstrip("/").rsplit("/", 1)[-1]
            yield chown(
                unix_path_join(repo, ".git", "worktrees", worktree_name),
                user,
                group,
                recursive=True,
            )
            branch_for_chown = new_branch
            if not branch_for_chown and not detached and not commitish:
                branch_for_chown = worktree_name
            if branch_for_chown:
                yield chown(
                    unix_path_join(repo, ".git", "refs", "heads", branch_for_chown),
                    user,
                    group,
                )
                yield chown(
                    unix_path_join(repo, ".git", "logs", "refs", "heads", branch_for_chown),
                    user,
                    group,
                    recursive=True,
                )

    # It exists and we don't want it
    elif host.get_fact(Directory, path=worktree) and not present:
        remove_args: list[str | QuoteString] = [
            "cd",
            QuoteString(worktree),
            "&&",
            "git",
            "worktree",
            "remove",
            ".",
        ]

        if force:
            remove_args.append("--force")

        yield StringCommand(*remove_args)

    # It exists and we still want it => pull/rebase it
    elif host.get_fact(Directory, path=worktree) and present:
        if not pull:
            host.noop("Pull is disabled")

        # pull the worktree only if it's already linked to a tracking branch or
        # if a remote branch is set
        elif host.get_fact(GitTrackingBranch, repo=worktree) or from_remote_branch:
            if from_remote_branch and (
                len(from_remote_branch) != 2 or type(from_remote_branch) not in (tuple, list)
            ):
                raise OperationError(
                    "The remote branch must be a 2-tuple (remote, branch) such as "
                    '("origin", "master")',
                )

            # Determine the remote ref we would pull from, so we can short-circuit
            # the pull when the worktree HEAD already matches the remote tip.
            remote_name: str | None = None
            remote_branch: str | None = None
            if from_remote_branch:
                remote_name, remote_branch = from_remote_branch[0], from_remote_branch[1]
            else:
                tracking = host.get_fact(GitTrackingBranch, repo=worktree)
                if tracking and "/" in tracking:
                    remote_name, remote_branch = tracking.split("/", 1)

            skip_pull = False
            if remote_name and remote_branch:
                local_commit = host.get_fact(GitLocalCommit, repo=worktree)
                remote_commit = host.get_fact(
                    GitRemoteBranchCommit,
                    repo=worktree,
                    remote=remote_name,
                    branch=remote_branch,
                )
                if local_commit and remote_commit and local_commit == remote_commit:
                    skip_pull = True

            if skip_pull:
                host.noop(
                    f"git worktree {worktree} is already up to date",
                )
            else:
                pull_args: list[str | QuoteString] = [
                    "cd",
                    QuoteString(worktree),
                    "&&",
                    "git",
                    "pull",
                ]

                if rebase:
                    pull_args.append("--rebase")

                if from_remote_branch:
                    pull_args.extend(
                        [
                            QuoteString(from_remote_branch[0]),
                            QuoteString(from_remote_branch[1]),
                        ]
                    )

                yield StringCommand(*pull_args)


@operation()
def bare_repo(
    path: str,
    user: str | None = None,
    group: str | None = None,
    present=True,
):
    """
    Create bare git repositories.

    + path: path to the folder
    + present: whether the bare repository should exist
    + user: chown files to this user after
    + group: chown files to this group after

    **Example:**

    .. code:: python

        git.bare_repo(
            name="Create bare repo",
            path="/home/git/test.git",
        )
    """

    yield from files.directory._inner(path, present=present)

    if present:
        head_filename = unix_path_join(path, "HEAD")
        head_file = host.get_fact(File, path=head_filename)

        if not head_file:
            yield StringCommand("git", "init", "--bare", QuoteString(path))
            if user or group:
                yield chown(path, user, group, recursive=True)
        else:
            if (user and head_file["user"] != user) or (group and head_file["group"] != group):
                yield chown(path, user, group, recursive=True)
