Apk
---


Mange apk packages.

:code:`apk.packages`
~~~~~~~~~~~~~~~~~~~~

Add/remove/update apk packages.

.. code:: python

    apk.packages(packages=None, present=True, latest=False, update=False, upgrade=False)

+ **packages**: list of packages to ensure
+ **present**: whether the packages should be installed
+ **latest**: whether to upgrade packages without a specified version
+ **update**: run apk update before installing packages
+ **upgrade**: run apk upgrade before installing packages

Versions:
    Package versions can be pinned like apk: ``<pkg>=<version>``.


:code:`apk.update`
~~~~~~~~~~~~~~~~~~

Updates apk repositories.

.. code:: python

    apk.update()


:code:`apk.upgrade`
~~~~~~~~~~~~~~~~~~~

Upgrades all apk packages.

.. code:: python

    apk.upgrade()

