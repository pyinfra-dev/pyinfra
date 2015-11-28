Git
---

:code:`git.repo`
~~~~~~~~~~~~~~~~

Manage git repositories.

.. code:: python

    git.repo(source, target, branch='master', pull=True, rebase=False)

+ **source**: the git source URL
+ **target**: target directory to clone to
+ **branch**: branch to pull/checkout
+ **pull**: pull any changes for the branch
+ **rebase**: when pulling, use ``--rebase``

