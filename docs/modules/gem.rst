Gem
---


Mange gem packages.

:code:`gem.packages`
~~~~~~~~~~~~~~~~~~~~

Manage gem packages.

.. code:: python

    gem.packages(packages=None, present=True, latest=False)

+ **packages**: list of packages to ensure
+ **present**: whether the packages should be installed
+ **latest**: whether to upgrade packages without a specified version

Versions:
    Package versions can be pinned like gem: ``<pkg>:<version>``

