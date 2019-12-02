'''
Manage git repositories and configuration.
'''

from __future__ import unicode_literals

import re

from pyinfra.api import operation, OperationError

from . import files, ssh
from .util.files import chown


@operation(pipeline_facts={
    'git_config': 'repo',
})
def config(
    state, host, key, value,
    repo=None,
):
    '''
    Manage git config for a repository or globally.

    + key: the key of the config to ensure
    + value: the value this key should have
    + repo: specify the git repo path to edit local config (defaults to global)

    Example:

    .. code:: python

        git.config(
            {'Ensure user name is set for a repo'},
            key='user.name',
            value='Anon E. Mouse',
            repo='/usr/local/src/pyinfra',
        )

    '''

    existing_config = host.fact.git_config(repo)

    if not existing_config or existing_config.get(key) != value:
        if repo is None:
            yield 'git config --global {0} "{1}"'.format(key, value)
        else:
            yield 'cd {0} && git config --local {1} "{2}"'.format(repo, key, value)


@operation(pipeline_facts={
    'git_branch': 'target',
})
def repo(
    state, host, source, target,
    branch='master', pull=True, rebase=False,
    user=None, group=None, ssh_keyscan=False,
    update_submodules=False, recursive_submodules=False,
):
    '''
    Clone/pull git repositories.

    + source: the git source URL
    + target: target directory to clone to
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
            {'Clone repo'},
            'https://github.com/Fizzadar/pyinfra.git',
            '/usr/local/src/pyinfra',
        )
    '''

    # Ensure our target directory exists
    yield files.directory(state, host, target)

    # Do we need to scan for the remote host key?
    if ssh_keyscan:
        # Attempt to parse the domain from the git repository
        domain = re.match(r'^[a-zA-Z0-9]+@([0-9a-zA-Z\.\-]+)', source)

        if domain:
            yield ssh.keyscan(state, host, domain.group(1))
        else:
            raise OperationError(
                'Could not parse domain (to SSH keyscan) from: {0}'.format(source),
            )

    # Store git commands for directory prefix
    git_commands = []
    is_repo = host.fact.directory('/'.join((target, '.git')))

    # Cloning new repo?
    if not is_repo:
        git_commands.append('clone {0} --branch {1} .'.format(source, branch))

    # Ensuring existing repo
    else:
        current_branch = host.fact.git_branch(target)
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
    command_prefix = 'cd {0} && git'.format(target)
    git_commands = [
        '{0} {1}'.format(command_prefix, command)
        for command in git_commands
    ]

    for cmd in git_commands:
        yield cmd

    # Apply any user or group
    if user or group:
        yield chown(target, user, group, recursive=True)
