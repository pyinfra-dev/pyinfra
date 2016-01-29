Npm
---

:code:`npm.packages`
~~~~~~~~~~~~~~~~~~~~

Manage npm packages.

.. code:: python

    npm.packages(packages=None, present=True, directory=None)

+ **packages**: list of packages to ensure
+ **present**: whether the packages should be present
+ **directory**: directory to manage packages for, defaults to global

Versions:
    Package versions can be pinned like npm: ``<pkg>@<version>``

