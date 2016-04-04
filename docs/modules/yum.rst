Yum
---


Manage yum packages and repositories. Note that yum package names are case-sensitive.

:code:`yum.key`
~~~~~~~~~~~~~~~

Add yum gpg keys with ``rpm``.

.. code:: python

    yum.key(key)

+ **key**: filename or URL

Note:
    always returns one command, not state checking


:code:`yum.packages`
~~~~~~~~~~~~~~~~~~~~

Manage yum packages & updates.

.. code:: python

    yum.packages(packages=None, present=True, latest=False, upgrade=False, clean=False)

+ **packages**: list of packages to ensure
+ **present**: whether the packages should be installed
+ **latest**: whether to upgrade packages without a specified version
+ **upgrade**: run yum upgrade
+ **clean**: run yum clean


:code:`yum.repo`
~~~~~~~~~~~~~~~~

Manage yum repositories.

.. code:: python

    yum.repo(name, baseurl, present=True, description=None, gpgcheck=True, enabled=True)

+ **name**: filename for the repo (in ``/etc/yum/repos.d/``)
+ **baseurl**: the baseurl of the repo
+ **present**: whether the ``.repo`` file should be present
+ **description**: optional verbose description
+ **gpgcheck**: whether set ``gpgcheck=1``


:code:`yum.rpm`
~~~~~~~~~~~~~~~

Install/manage ``.rpm`` file packages.

.. code:: python

    yum.rpm(source, present=True)

+ **source**: filenameo or URL of the ``.rpm`` package
+ **present**: whether ore not the package should exist on the system

URL sources with ``present=False``:
    if the ``.rpm`` file isn't downloaded, pyinfra can't remove any existing package
    as the file won't exist until mid-deploy

