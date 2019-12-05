Pacman
------


Mange pacman packages.

:code:`pacman.packages`
~~~~~~~~~~~~~~~~~~~~~~~

Add/remove pacman packages.

.. code:: python

    pacman.packages(packages=None, present=True, update=False, upgrade=False)

+ **packages**: list of packages to ensure
+ **present**: whether the packages should be installed
+ **update**: run pacman -Sy before installing packages
+ **upgrade**: run pacman -Syu before installing packages

Versions:
    Package versions can be pinned like pacman: ``<pkg>=<version>``.


:code:`pacman.update`
~~~~~~~~~~~~~~~~~~~~~

Updates pacman repositories.

.. code:: python

    pacman.update()


:code:`pacman.upgrade`
~~~~~~~~~~~~~~~~~~~~~~

Upgrades all pacman packages.

.. code:: python

    pacman.upgrade()

