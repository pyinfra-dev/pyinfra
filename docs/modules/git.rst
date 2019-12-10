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
        ssh_keyscan=False, update_submodules=False, recursive_submodules=False
    )

+ **source**: the git source URL
+ **target**: target directory to clone to
+ **branch**: branch to pull/checkout
+ **pull**: pull any changes for the branch
+ **rebase**: when pulling, use ``--rebase``
+ **user**: chown files to this user after
+ **group**: chown files to this group after
+ **ssh_keyscan**: keyscan the remote host if not in known_hosts before clone/pull
+ **update_submodules**: update any git submodules
+ **recursive_submodules**: update git submodules recursively

