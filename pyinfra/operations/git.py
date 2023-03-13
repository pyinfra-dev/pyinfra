"""
Manage git repositories and configuration.
"""

import re

from pyinfra import host
from pyinfra.api import OperationError, operation
from pyinfra.facts.files import Directory, File
from pyinfra.facts.git import GitBranch, GitConfig, GitTrackingBranch

from . import files, ssh
from .util.files import chown, unix_path_join


@operation(
    pipeline_facts={"git_config": "repo"},
)
def config(key, value, multi_value=False, repo=None):
    """
    Manage git config for a repository or globally.

    + key: the key of the config to ensure
    + value: the value this key should have
    + multi_value: Add the value rather than set it for settings that can have multiple values
    + repo: specify the git repo path to edit local config (defaults to global)

    **Example:**

    .. code:: python

        git.config(
            name="Ensure user name is set for a repo",
            key="user.name",
            value="Anon E. Mouse",
            repo="/usr/local/src/pyinfra",
        )

    """

    existing_config = {}

    if not repo:
        existing_config = host.get_fact(GitConfig)

    # Only get the config if the repo exists at this stage
    elif host.get_fact(Directory, path=unix_path_join(repo, ".git")):
        existing_config = host.get_fact(GitConfig, repo=repo)

    if repo is None:
        base_command = "git config --global"
    else:
        base_command = "cd {0} && git config --local".format(repo)

    if not multi_value and existing_config.get(key) != [value]:
        yield '{0} {1} "{2}"'.format(base_command, key, value)
        existing_config[key] = [value]

    elif multi_value and value not in existing_config.get(key, []):
        yield '{0} --add {1} "{2}"'.format(base_command, key, value)
        existing_config.setdefault(key, []).append(value)

    else:
        host.noop("git config {0} is set to {1}".format(key, value))


@operation(
    pipeline_facts={"git_branch": "target"},
)
def repo(
    src,
    dest,
    branch=None,
    pull=True,
    rebase=False,
    user=None,
    group=None,
    ssh_keyscan=False,
    update_submodules=False,
    recursive_submodules=False,
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

    **Example:**

    .. code:: python

        git.repo(
            name="Clone repo",
            src="https://github.com/Fizzadar/pyinfra.git",
            dest="/usr/local/src/pyinfra",
        )
    """

    # Ensure our target directory exists
    yield from files.directory(dest)

    # Do we need to scan for the remote host key?
    if ssh_keyscan:
        # Attempt to parse the domain from the git repository
        domain = re.match(r"^[a-zA-Z0-9]+@([0-9a-zA-Z\.\-]+)", src)

        if domain:
            yield from ssh.keyscan(domain.group(1))
        else:
            raise OperationError(
                "Could not parse domain (to SSH keyscan) from: {0}".format(src),
            )

    # Store git commands for directory prefix
    git_commands = []
    git_dir = unix_path_join(dest, ".git")
    is_repo = host.get_fact(Directory, path=git_dir)

    # Cloning new repo?
    if not is_repo:
        if branch:
            git_commands.append("clone {0} --branch {1} .".format(src, branch))
        else:
            git_commands.append("clone {0} .".format(src))

        host.create_fact(GitBranch, kwargs={"repo": dest}, data=branch)
        host.create_fact(
            Directory,
            kwargs={"path": git_dir},
            data={"user": user, "group": group},
        )

    # Ensuring existing repo
    else:
        if branch and host.get_fact(GitBranch, repo=dest) != branch:
            git_commands.append("fetch")  # fetch to ensure we have the branch locally
            git_commands.append("checkout {0}".format(branch))
            host.create_fact(GitBranch, kwargs={"repo": dest}, data=branch)

        if pull:
            if rebase:
                git_commands.append("pull --rebase")
            else:
                git_commands.append("pull")

    if update_submodules:
        if recursive_submodules:
            git_commands.append("submodule update --init --recursive")
        else:
            git_commands.append("submodule update --init")

    # Attach prefixes for directory
    command_prefix = "cd {0} && git".format(dest)
    git_commands = ["{0} {1}".format(command_prefix, command) for command in git_commands]

    for cmd in git_commands:
        yield cmd

    # Apply any user or group if we did anything
    if git_commands and (user or group):
        yield chown(dest, user, group, recursive=True)


@operation()
def worktree(
    worktree,
    repo=None,
    detached=False,
    new_branch=None,
    commitish=None,
    pull=True,
    rebase=False,
    from_remote_branch=None,
    present=True,
    assume_repo_exists=False,
    force=False,
    user=None,
    group=None,
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
    + force: remove unclean working tree if should not exist
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
                "The following folder is not a valid GIT repository : {0}".format(repo),
            )

        command_parts = ["cd {0} && git worktree add".format(repo)]

        if new_branch:
            command_parts.append("-b {0}".format(new_branch))
        elif detached:
            command_parts.append("--detach")

        command_parts.append(worktree)

        if commitish:
            command_parts.append(commitish)

        yield " ".join(command_parts)

        # Apply any user or group
        if user or group:
            yield chown(worktree, user, group, recursive=True)

        host.create_fact(Directory, kwargs={"path": worktree}, data={"user": user, "group": group})
        host.create_fact(GitTrackingBranch, kwargs={"repo": worktree}, data=new_branch)

    # It exists and we don't want it
    elif host.get_fact(Directory, path=worktree) and not present:

        command = "cd {0} && git worktree remove .".format(worktree)

        if force:
            command += " --force"

        yield command

        host.delete_fact(Directory, kwargs={"path": worktree})
        host.create_fact(GitTrackingBranch, kwargs={"repo": worktree})

    # It exists and we still want it => pull/rebase it
    elif host.get_fact(Directory, path=worktree) and present:

        # pull the worktree only if it's already linked to a tracking branch or
        # if a remote branch is set
        if host.get_fact(GitTrackingBranch, repo=worktree) or from_remote_branch:
            command = "cd {0} && git pull".format(worktree)

            if rebase:
                command += " --rebase"

            if from_remote_branch:
                if len(from_remote_branch) != 2 or type(from_remote_branch) not in (tuple, list):
                    raise OperationError(
                        "The remote branch must be a 2-tuple (remote, branch) such as "
                        '("origin", "master")',
                    )
                command += " {0} {1}".format(*from_remote_branch)

            yield command


@operation
def bare_repo(
    path,
    user=None,
    group=None,
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

    yield from files.directory(path, present=present)

    if present:
        head_filename = unix_path_join(path, "HEAD")
        head_file = host.get_fact(File, path=head_filename)

        if not head_file:
            yield "git init --bare {0}".format(path)
            if user or group:
                yield chown(path, user, group, recursive=True)
        else:
            if (user and head_file["user"] != user) or (group and head_file["group"] != group):
                yield chown(path, user, group, recursive=True)

        host.create_fact(
            File,
            kwargs={"path": head_filename},
            data={"user": user, "group": group, "mode": None},
        )
