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

Install/remove/update yum packages & updates.

.. code:: python

    yum.packages(packages=None, present=True, latest=False, update=False, clean=False)

+ **packages**: list of packages to ensure
+ **present**: whether the packages should be installed
+ **latest**: whether to upgrade packages without a specified version
+ **update**: run yum update
+ **clean**: run yum clean

Versions:
    Package versions can be pinned like yum: ``<pkg>-<version>``


:code:`yum.repo`
~~~~~~~~~~~~~~~~

Add/remove/update yum repositories.

.. code:: python

    yum.repo(name, baseurl, present=True, description=None, enabled=True, gpgcheck=True, gpgkey=None)

+ **name**: filename for the repo (in ``/etc/yum/repos.d/``)
+ **baseurl**: the baseurl of the repo
+ **present**: whether the ``.repo`` file should be present
+ **description**: optional verbose description
+ **gpgcheck**: whether set ``gpgcheck=1``
+ **gpgkey**: the URL to the gpg key for this repo


:code:`yum.rpm`
~~~~~~~~~~~~~~~

Add/remove ``.rpm`` file packages.

.. code:: python

    yum.rpm(source, present=True)

+ **source**: filename or URL of the ``.rpm`` package
+ **present**: whether ore not the package should exist on the system

URL sources with ``present=False``:
    If the ``.rpm`` file isn't downloaded, pyinfra can't remove any existing
    package as the file won't exist until mid-deploy.


:code:`yum.update`
~~~~~~~~~~~~~~~~~~

Updates all yum packages.

.. code:: python

    yum.update()

