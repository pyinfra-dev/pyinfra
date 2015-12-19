Apt
---


Manage apt packages and repositories.

:code:`apt.packages`
~~~~~~~~~~~~~~~~~~~~

Install/remove/upgrade packages & update apt.

.. code:: python

    apt.packages(packages=None, present=True, update=False, cache_time=None, upgrade=False)

+ **packages**: list of packages to ensure
+ **present**: whether the packages should be installed
+ **update**: run apt update
+ **cache_time**: when used with update, cache for this many seconds
+ **upgrade**: run apt upgrade

Note:
    ``cache_time`` only works on systems that provide the
    ``/var/lib/apt/periodic/update-success-stamp`` file (ie Ubuntu).


:code:`apt.repo`
~~~~~~~~~~~~~~~~

Manage apt source repositories. Options:

.. code:: python

    apt.repo(name, present=True)

+ **name**: apt line, repo url or PPA
+ **present**: whether the repo should exist on the system

