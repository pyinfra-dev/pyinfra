Pkg
---


Manage BSD packages and repositories. Note that BSD package names are case-sensitive.

:code:`pkg.packages`
~~~~~~~~~~~~~~~~~~~~

Manage pkg_* packages.

.. code:: python

    pkg.packages(packages=None, present=True)

+ **packages**: list of packages to ensure
+ **present**: whether the packages should be installed

