Apt
---


Manage apt packages and repositories.

:code:`apt.deb`
~~~~~~~~~~~~~~~

Install/manage ``.deb`` file packages.

.. code:: python

    apt.deb(source, present=True)

+ **source**: filename or URL of the ``.deb`` file
+ **present**: whether or not the package should exist on the system

Note:
    when installing, ``apt-get install -f`` will be run to install any unmet
    dependencies

URL sources with ``present=False``:
    if the ``.deb`` file isn't downloaded, pyinfra can't remove any existing package
    as the file won't exist until mid-deploy


:code:`apt.key`
~~~~~~~~~~~~~~~

Add apt gpg keys with ``apt-key``.

.. code:: python

    apt.key(key)

+ **key**: filename or URL

Note:
    always returns an add command, not state checking


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

Versions:
    Package versions can be pinned like apt: ``<pkg>=<version>``

Note:
    ``cache_time`` only works on systems that provide the
    ``/var/lib/apt/periodic/update-success-stamp`` file (ie Ubuntu).


:code:`apt.repo`
~~~~~~~~~~~~~~~~

Manage apt repositories.

.. code:: python

    apt.repo(name, present=True)

+ **name**: apt line, repo url or PPA
+ **present**: whether the repo should exist on the system

