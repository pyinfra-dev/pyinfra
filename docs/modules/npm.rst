Npm
---

:code:`npm.packages`
~~~~~~~~~~~~~~~~~~~~

Install/remove/update npm packages.

.. code:: python

    npm.packages(packages=None, present=True, latest=False, directory=None)

+ **packages**: list of packages to ensure
+ **present**: whether the packages should be present
+ **latest**: whether to upgrade packages without a specified version
+ **directory**: directory to manage packages for, defaults to global

Versions:
    Package versions can be pinned like npm: ``<pkg>@<version>``.

