Git
---

:code:`git.repo`
~~~~~~~~~~~~~~~~

Manage git repositories.

.. code:: python

    git.repo(
        source, target, branch='master', pull=True,
        rebase=False, user=None, group=None, use_ssh_user=False, ssh_keyscan=False
    )

+ **source**: the git source URL
+ **target**: target directory to clone to
+ **branch**: branch to pull/checkout
+ **pull**: pull any changes for the branch
+ **rebase**: when pulling, use ``--rebase``
+ **user**: chown files to this user after
+ **group**: chown files to this group after
+ **use_ssh_user**: whether to use the SSH user to clone/pull
+ **ssh_keyscan**: keyscan the remote host if not in known_hosts before clone/pull

SSH user:
    This is essentially a hack to bypass the fact that sudo doesn't carry SSH agent:

    * makes the target directory writeable by all
    * clones/pulls w/o sudo as the connecting SSH user
    * removes other/group write permissions - unless group is defined, in which case
      only other

