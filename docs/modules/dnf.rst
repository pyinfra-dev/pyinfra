Dnf
---


Manage dnf packages and repositories. Note that dnf package names are case-sensitive.

:code:`dnf.key`
~~~~~~~~~~~~~~~

Add dnf gpg keys with ``rpm``.

.. code:: python

    dnf.key(key)

+ **key**: filename or URL

Note:
    always returns one command, not state checking


:code:`dnf.packages`
~~~~~~~~~~~~~~~~~~~~

Install/remove/update dnf packages & updates.

.. code:: python

    dnf.packages(packages=None, present=True, latest=False, update=False, clean=False)

+ **packages**: list of packages to ensure
+ **present**: whether the packages should be installed
+ **latest**: whether to upgrade packages without a specified version
+ **update**: run dnf update
+ **clean**: run dnf clean

Versions:
    Package versions can be pinned like dnf: ``<pkg>-<version>``


:code:`dnf.repo`
~~~~~~~~~~~~~~~~

Add/remove/update dnf repositories.

.. code:: python

    dnf.repo(name, baseurl, present=True, description=None, enabled=True, gpgcheck=True, gpgkey=None)

+ **name**: filename for the repo (in ``/etc/dnf/repos.d/``)
+ **baseurl**: the baseurl of the repo
+ **present**: whether the ``.repo`` file should be present
+ **description**: optional verbose description
+ **gpgcheck**: whether set ``gpgcheck=1``
+ **gpgkey**: the URL to the gpg key for this repo


:code:`dnf.rpm`
~~~~~~~~~~~~~~~

Add/remove ``.rpm`` file packages.

.. code:: python

    dnf.rpm(source, present=True)

+ **source**: filename or URL of the ``.rpm`` package
+ **present**: whether ore not the package should exist on the system

URL sources with ``present=False``:
    If the ``.rpm`` file isn't downloaded, pyinfra can't remove any existing
    package as the file won't exist until mid-deploy.


:code:`dnf.update`
~~~~~~~~~~~~~~~~~~

Updates all dnf packages.

.. code:: python

    dnf.update()

