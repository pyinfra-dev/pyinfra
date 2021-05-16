'''
Manage git repositories and configuration.
'''

from __future__ import unicode_literals

import re

from pyinfra import logger
from pyinfra.api import operation, OperationError

from . import files, ssh
from .util.files import chown


@operation(pipeline_facts={
    'git_config': 'repo',
})
def config(
    key, value,
    repo=None,
    state=None, host=None,
):
    '''
    Manage git config for a repository or globally.

    + key: the key of the config to ensure
    + value: the value this key should have
    + repo: specify the git repo path to edit local config (defaults to global)

    Example:

    .. code:: python

        git.config(
            name='Ensure user name is set for a repo',
            key='user.name',
            value='Anon E. Mouse',
            repo='/usr/local/src/pyinfra',
        )

    '''

    existing_config = {}

    if not repo:
        existing_config = host.fact.git_config()

    # Only get the config if the repo exists at this stage
    elif host.fact.directory('/'.join((repo, '.git'))):
        existing_config = host.fact.git_config(repo)

    if existing_config.get(key) != value:
        if repo is None:
            yield 'git config --global {0} "{1}"'.format(key, value)
        else:
            yield 'cd {0} && git config --local {1} "{2}"'.format(repo, key, value)

        existing_config[key] = value

    else:
        host.noop('git config {0} is set to {1}'.format(key, value))


@operation(pipeline_facts={
    'git_branch': 'target',
})
def repo(
    src, dest,
    branch='master',  # TODO: change the default to None
    pull=True, rebase=False,
    user=None, group=None, ssh_keyscan=False,
    update_submodules=False, recursive_submodules=False,
    state=None, host=None,
):
    '''
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

    Example:

    .. code:: python

        git.repo(
            name='Clone repo',
            src='https://github.com/Fizzadar/pyinfra.git',
            dest='/usr/local/src/pyinfra',
        )
    '''

    # Ensure our target directory exists
    yield files.directory(dest, state=state, host=host)

    # Do we need to scan for the remote host key?
    if ssh_keyscan:
        # Attempt to parse the domain from the git repository
        domain = re.match(r'^[a-zA-Z0-9]+@([0-9a-zA-Z\.\-]+)', src)

        if domain:
            yield ssh.keyscan(domain.group(1), state=state, host=host)
        else:
            raise OperationError(
                'Could not parse domain (to SSH keyscan) from: {0}'.format(src),
            )

    # Store git commands for directory prefix
    git_commands = []
    is_repo = host.fact.directory('/'.join((dest, '.git')))

    # Cloning new repo?
    if not is_repo:
        if branch:
            git_commands.append('clone {0} --branch {1} .'.format(src, branch))
        else:
            git_commands.append('clone {0} .'.format(src))

    # Ensuring existing repo
    else:
        current_branch = host.fact.git_branch(dest)
        if current_branch != branch:
            git_commands.append('fetch')  # fetch to ensure we have the branch locally
            git_commands.append('checkout {0}'.format(branch))

        if pull:
            if rebase:
                git_commands.append('pull --rebase')
            else:
                git_commands.append('pull')

    if update_submodules:
        if recursive_submodules:
            git_commands.append('submodule update --init --recursive')
        else:
            git_commands.append('submodule update --init')

    # Attach prefixes for directory
    command_prefix = 'cd {0} && git'.format(dest)
    git_commands = [
        '{0} {1}'.format(command_prefix, command)
        for command in git_commands
    ]

    for cmd in git_commands:
        yield cmd

    # Apply any user or group
    if user or group:
        yield chown(dest, user, group, recursive=True)


@operation()
def worktree(
    worktree,
    repo=None, branch=None, create_branch=False, detached=False,
    new_branch=None, commitish=None,
    pull=True, rebase=False, from_remote_branch=None,
    present=True, assume_repo_exists=False, force=False,
    user=None, group=None, state=None, host=None,
):
    '''
    Manage git worktrees.

    + worktree: git working tree directory
    + repo: git main repository directory
    + detached: create a working tree with a detached HEAD
    + branch: (deprecated)
    + create_branch: (deprecated)
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

    Example:

    .. code:: python

        git.worktree(
            name='Create a worktree from the current repo `HEAD`',
            repo='/usr/local/src/pyinfra/master',
            worktree='/usr/local/src/pyinfra/hotfix'
        )

        git.worktree(
            name='Create a worktree from the commit `4e091aa0`',
            repo='/usr/local/src/pyinfra/master',
            worktree='/usr/local/src/pyinfra/hotfix',
            commitish='4e091aa0'
        )

        git.worktree(
            name='Create a worktree with a new local branch `v1.0`',
            repo='/usr/local/src/pyinfra/master',
            worktree='/usr/local/src/pyinfra/hotfix',
            new_branch='v1.0',
        )

        git.worktree(
            name='Create a worktree from the commit 4e091aa0 with the new local branch `v1.0`',
            repo='/usr/local/src/pyinfra/master',
            worktree='/usr/local/src/pyinfra/hotfix',
            new_branch='v1.0',
            commitish='4e091aa0'
        )

        git.worktree(
            name='Create a worktree with a detached `HEAD`',
            repo='/usr/local/src/pyinfra/master',
            worktree='/usr/local/src/pyinfra/hotfix',
            detached=True,
        )

        git.worktree(
            name='Create a worktree with a detached `HEAD` from commit `4e091aa0`',
            repo='/usr/local/src/pyinfra/master',
            worktree='/usr/local/src/pyinfra/hotfix',
            commitish='4e091aa0',
            detached=True,
        )

        git.worktree(
            name='Create a worktree from the existing local branch `v1.0`',
            repo='/usr/local/src/pyinfra/master',
            worktree='/usr/local/src/pyinfra/hotfix',
            commitish='v1.0'
        )

        git.worktree(
            name='Create a worktree with a new branch `v1.0` that tracks `origin/v1.0`',
            repo='/usr/local/src/pyinfra/master',
            worktree='/usr/local/src/pyinfra/hotfix',
            new_branch='v1.0',
            commitish='v1.0'
        )

        git.worktree(
            name='Pull an existing worktree already linked to a tracking branch',
            repo='/usr/local/src/pyinfra/master',
            worktree='/usr/local/src/pyinfra/hotfix'
        )

        git.worktree(
            name='Pull an existing worktree from a specific remote branch',
            repo='/usr/local/src/pyinfra/master',
            worktree='/usr/local/src/pyinfra/hotfix',
            from_remote_branch=('origin', 'master')
        )

        git.worktree(
            name='Remove a worktree',
            worktree='/usr/local/src/pyinfra/hotfix',
            present=False,
        )

        git.worktree(
            name='Remove an unclean worktree',
            worktree='/usr/local/src/pyinfra/hotfix',
            present=False,
            force=True,
        )
    '''

    # handle deprecated arguments.
    #  1) old api: branch=xxx, create_branch=True => git worktree add -b xxx <worktree_path>
    #     new api: new_branch=xxx
    #
    #  2) old api: branch=xxx, create_branch=False => git worktree add <worktree_path> xxx
    #     new api: commitish=xxx
    if branch:
        logger.warning(
            'The `branch` and `create_branch` arguments are deprecated. '
            'Please use `branch` and `commitish`.',
        )

        if create_branch:
            if new_branch:
                raise OperationError(
                    'The deprecated arguments `branch` and `create_branch` are not compatible with'
                    ' the new `branch` argument. Please use the new `branch` argument only.',
                )
            else:
                new_branch = branch
        else:
            if commitish:
                raise OperationError(
                    'The deprecated arguments `branch` and `create_branch` are not compatible with'
                    ' the new `commitish` argument. Please use the new `commitish` argument only.',
                )
            else:
                commitish = branch

    # Doesn't exist & we want it
    if not host.fact.directory(worktree) and present:

        # be sure that `repo` is a GIT repository
        if not assume_repo_exists and not host.fact.directory('/'.join((repo, '.git'))):
            raise OperationError(
                'The following folder is not a valid GIT repository : {0}'.format(repo),
            )

        command_parts = ['cd {0} && git worktree add'.format(repo)]

        if new_branch:
            command_parts.append('-b {0}'.format(new_branch))
        elif detached:
            command_parts.append('--detach')

        command_parts.append(worktree)

        if commitish:
            command_parts.append(commitish)

        yield ' '.join(command_parts)

        # Apply any user or group
        if user or group:
            yield chown(worktree, user, group, recursive=True)

    # It exists and we don't want it
    elif host.fact.directory(worktree) and not present:

        command = 'cd {0} && git worktree remove .'.format(worktree)

        if force:
            command += ' --force'

        yield command

    # It exists and we still want it => pull/rebase it
    elif host.fact.directory(worktree) and present:

        # pull the worktree only if it's already linked to a tracking branch or
        # if a remote branch is set
        if host.fact.git_tracking_branch(worktree) or from_remote_branch:
            command = 'cd {0} && git pull'.format(worktree)

            if rebase:
                command += ' --rebase'

            if from_remote_branch:
                if len(from_remote_branch) != 2 or type(from_remote_branch) not in (tuple, list):
                    raise OperationError(
                        'The remote branch must be a 2-tuple (remote, branch) such as '
                        '("origin", "master")',
                    )
                command += ' {0} {1}'.format(*from_remote_branch)

            yield command


@operation
def bare_repo(
    path,
    user=None,
    group=None,
    present=True,
    state=None,
    host=None,
):
    '''
    Create bare git repositories.

    + path: path to the folder
    + present: whether the bare repository should exist
    + user: chown files to this user after
    + group: chown files to this group after

    Example:

    .. code:: python

        git.bare_repo(
            name='Create bare repo',
            path='/home/git/test.git',
        )
    '''

    yield files.directory(path, state=state, host=host, present=present)

    # Ensure our target directory exists
    if present:
        yield 'git init --bare {0}'.format(path)

    # Apply any user or group
    if user or group:
        yield chown(path, user, group, recursive=True)
