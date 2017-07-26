# pyinfra
# File: pyinfra/modules/git.py
# Desc: manage git repositories

'''
Manage git repositories and configuration.
'''

from __future__ import unicode_literals

import re

from pyinfra import logger
from pyinfra.api import operation

from . import files, ssh
from .util.files import chmod, chown


@operation(pipeline_facts={
    'git_branch': 'target',
})
def repo(
    state, host, source, target,
    branch='master', pull=True, rebase=False,
    user=None, group=None, use_ssh_user=False, ssh_keyscan=False,
):
    '''
    Manage git repositories.

    + source: the git source URL
    + target: target directory to clone to
    + branch: branch to pull/checkout
    + pull: pull any changes for the branch
    + rebase: when pulling, use ``--rebase``
    + user: chown files to this user after
    + group: chown files to this group after
    + ssh_keyscan: keyscan the remote host if not in known_hosts before clone/pull

    + [DEPRECATED] use_ssh_user: whether to use the SSH user to clone/pull

    SSH user (deprecated, please use ``preserve_sudo_env``):
        This is an old hack from pyinfra <0.4 which did not support the global
        kwarg ``preserve_sudo_env``. It does the following:

        * makes the target directory writeable by all
        * clones/pulls w/o sudo as the connecting SSH user
        * removes other/group write permissions - unless group is defined, in
          which case only other
    '''

    if use_ssh_user:
        logger.warning(
            'Use of `use_ssh_user` is deprecated, please use `preserve_sudo_env` instead.',
        )

    # Ensure our target directory exists
    yield files.directory(state, host, target)

    # If we're going to chown this after clone/pull, and we're sudo'd, we need to make the
    # directory writeable by the SSH user
    if use_ssh_user:
        yield chmod(target, 'go+w', recursive=True)

    # Do we need to scan for the remote host key?
    if ssh_keyscan:
        # Attempt to parse the domain from the git repository
        domain = re.match(r'^[a-zA-Z0-9]+@([0-9a-zA-Z\.\-]+)', source)

        if domain:
            yield ssh.keyscan(state, host, domain.group(1))

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
            git_commands.append('checkout {0}'.format(branch))

        if pull:
            if rebase:
                git_commands.append('pull --rebase')
            else:
                git_commands.append('pull')

    # Attach prefixes for directory
    command_prefix = 'cd {0} && git'.format(target)
    git_commands = [
        '{0} {1}'.format(command_prefix, command)
        for command in git_commands
    ]

    if use_ssh_user:
        git_commands = [
            {
                'command': command,
                'sudo': False,
                'sudo_user': False,
            }
            for command in git_commands
        ]

    for cmd in git_commands:
        yield cmd

    if use_ssh_user:
        # Remove write permissions from other or other+group when no group
        yield chmod(
            target,
            'o-w' if group else 'go-w',
            recursive=True,
        )

    # Apply any user or group
    if user or group:
        yield chown(target, user, group, recursive=True)
