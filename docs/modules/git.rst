Git
---


Manage git repositories and configuration.

:code:`git.config`
~~~~~~~~~~~~~~~~~~

Manage git config for a repository or globally.

.. code:: python

    git.config(key, value, repo=None)

+ **key**: the key of the config to ensure
+ **value**: the value this key should have
+ **repo**: specify the git repo path to edit local config (defaults to global)


:code:`git.repo`
~~~~~~~~~~~~~~~~

Clone/pull git repositories.

.. code:: python

    git.repo(
        source, target, branch='master', pull=True, rebase=False, user=None, group=None,
        use_ssh_user=False, ssh_keyscan=False, update_submodules=False, recursive_submodules=False
    )

+ **source**: the git source URL
+ **target**: target directory to clone to
+ **branch**: branch to pull/checkout
+ **pull**: pull any changes for the branch
+ **rebase**: when pulling, use ``--rebase``
+ **user**: chown files to this user after
+ **group**: chown files to this group after
+ **ssh_keyscan**: keyscan the remote host if not in known_hosts before clone/pull
+ **update_submodules**: update any submodules in the repository
+ **recursive_submodules**: recursively update submodules in the repository

+ [DEPRECATED] use_ssh_user: whether to use the SSH user to clone/pull

SSH user (deprecated, please use ``preserve_sudo_env``):
    This is an old hack from pyinfra <0.4 which did not support the global
    kwarg ``preserve_sudo_env``. It does the following:

    * makes the target directory writeable by all
    * clones/pulls w/o sudo as the connecting SSH user
    * removes other/group write permissions - unless group is defined, in
      which case only other

