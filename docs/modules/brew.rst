Brew
----


Mange brew packages.

:code:`brew.cask_upgrade`
~~~~~~~~~~~~~~~~~~~~~~~~~

Upgrades all brew casks.

.. code:: python

    brew.cask_upgrade()


:code:`brew.casks`
~~~~~~~~~~~~~~~~~~

Add/remove/update brew casks.

.. code:: python

    brew.casks(packages=None, present=True, latest=False, upgrade=False)

+ **packages**: list of packages to ensure
+ **present**: whether the packages should be installed
+ **latest**: whether to upgrade packages without a specified version
+ **upgrade**: run brew cask upgrade before installing packages

Versions:
    Package versions can be pinned like brew: ``<pkg>@<version>``.


:code:`brew.packages`
~~~~~~~~~~~~~~~~~~~~~

Add/remove/update brew packages.

.. code:: python

    brew.packages(packages=None, present=True, latest=False, update=False, upgrade=False)

+ **packages**: list of packages to ensure
+ **present**: whether the packages should be installed
+ **latest**: whether to upgrade packages without a specified version
+ **update**: run brew update before installing packages
+ **upgrade**: run brew upgrade before installing packages

Versions:
    Package versions can be pinned like brew: ``<pkg>@<version>``.


:code:`brew.tap`
~~~~~~~~~~~~~~~~

Add/remove brew taps.

.. code:: python

    brew.tap(name, present=True)

+ **name**: the name of the tasp
+ **present**: whether this tap should be present or not


:code:`brew.update`
~~~~~~~~~~~~~~~~~~~

Updates brew repositories.

.. code:: python

    brew.update()


:code:`brew.upgrade`
~~~~~~~~~~~~~~~~~~~~

Upgrades all brew packages.

.. code:: python

    brew.upgrade()

