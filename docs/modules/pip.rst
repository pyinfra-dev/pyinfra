Pip
---


Manage pip packages. Compatible globally or inside a virtualenv.

:code:`pip.packages`
~~~~~~~~~~~~~~~~~~~~

Manage pip packages.

.. code:: python

    pip.packages(packages=None, present=True, latest=False, requirements=None, virtualenv=None)

+ **packages**: list of packages to ensure
+ **present**: whether the packages should be installed
+ **latest**: whether to upgrade packages without a specified version
+ **requirements**: location of requirements file to install
+ **virtualenv**: root directory of virtualenv to work in

Versions:
    Package versions can be pinned like pip: ``<pkg>==<version>``


:code:`pip.virtualenv`
~~~~~~~~~~~~~~~~~~~~~~

Manage virtualenv.

.. code:: python

    pip.virtualenv(path, python=None, site_packages=False, always_copy=False, present=True)

+ **python**: python interpreter to use
+ **site_packages**: give access to the global site-packages
+ **always_copy**: always copy files rather than symlinking
+ **present**: whether the virtualenv should be installed

