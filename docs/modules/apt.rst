Apt
---


Manage apt packages and repositories.

:code:`apt.apt_update`
~~~~~~~~~~~~~~~~~~~~~~
.. code:: python

    apt.apt_update()


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

    apt.key(key=None, keyserver=None, keyid=None)

+ **key**: filename or URL
+ **keyserver**: URL of keyserver to fetch key from
+ **keyid**: key identifier when using keyserver

Note:
    Always returns an add command, not state checking.

keyserver/id:
    These must be provided together.


:code:`apt.packages`
~~~~~~~~~~~~~~~~~~~~

Install/remove/upgrade packages & update apt.

.. code:: python

    apt.packages(packages=None, present=True, latest=False, update=False, cache_time=None, upgrade=False)

+ **packages**: list of packages to ensure
+ **present**: whether the packages should be installed
+ **latest**: whether to upgrade packages without a specified version
+ **update**: run apt update
+ **cache_time**: when used with update, cache for this many seconds
+ **upgrade**: run apt upgrade

Versions:
    Package versions can be pinned like apt: ``<pkg>=<version>``

Note:
    ``cache_time`` only works on systems that provide the
    ``/var/lib/apt/periodic/update-success-stamp`` file (ie Ubuntu).


:code:`apt.ppa`
~~~~~~~~~~~~~~~

Manage Ubuntu ppa repositories.

.. code:: python

    apt.ppa(name, present=True)

+ **name**: the PPA name
+ **present**: whether it should exist

Note:
    requires ``apt-add-repository`` on the remote host


:code:`apt.repo`
~~~~~~~~~~~~~~~~

Manage apt repositories.

.. code:: python

    apt.repo(name, present=True, filename=None)

+ **name**: apt source string eg ``deb http://X hardy main``
+ **present**: whether the repo should exist on the system
+ **filename**: optional filename to use ``/etc/apt/sources.list.d/<filename>.list``. By
  default uses ``/etc/apt/sources.list``.


:code:`apt.update`
~~~~~~~~~~~~~~~~~~
.. code:: python

    apt.update()

