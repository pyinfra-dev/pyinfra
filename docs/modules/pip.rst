Pip
---


Manage pip packages. Compatible globally or inside a virtualenv.

:code:`pip.packages`
~~~~~~~~~~~~~~~~~~~~

Manage pip packages.

.. code:: python

    pip.packages(
        packages=None, present=True, latest=False, requirements=None, pip='pip', virtualenv=None,
        virtualenv_kwargs=None
    )

+ **packages**: list of packages to ensure
+ **present**: whether the packages should be installed
+ **latest**: whether to upgrade packages without a specified version
+ **requirements**: location of requirements file to install
+ **pip**: name or path of the pip directory to use
+ **virtualenv**: root directory of virtualenv to work in
+ **virtualenv_kwargs**: dictionary of arguments to pass to ``pip.virtualenv``

Virtualenv:
    This will be created if it does not exist already. ``virtualenv_kwargs``
    will be passed to ``pip.virtualenv`` which can be used to control how
    the env is created.

Versions:
    Package versions can be pinned like pip: ``<pkg>==<version>``.


:code:`pip.virtualenv`
~~~~~~~~~~~~~~~~~~~~~~

Manage Python virtualenvs.

.. code:: python

    pip.virtualenv(path, python=None, site_packages=False, always_copy=False, present=True)

+ **python**: python interpreter to use
+ **site_packages**: give access to the global site-packages
+ **always_copy**: always copy files rather than symlinking
+ **present**: whether the virtualenv should exist

