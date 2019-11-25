Server
------

:code:`arch`
~~~~~~~~~~~~

.. code:: python

    host.fact.arch


Returns the system architecture according to ``uname``.



:code:`command`
~~~~~~~~~~~~~~~

.. code:: python

    host.fact.command(command)


Returns the raw output lines of a given command.



:code:`crontab`
~~~~~~~~~~~~~~~

.. code:: python

    host.fact.crontab(user=None)


Returns a dictionary of cron command -> execution time.

.. code:: python

    '/path/to/command': {
        'minute': '*',
        'hour': '*',
        'month': '*',
        'day_of_month': '*',
        'day_of_week': '*',
    },
    ...



:code:`date`
~~~~~~~~~~~~

.. code:: python

    host.fact.date


Returns the current datetime on the server.



:code:`groups`
~~~~~~~~~~~~~~

.. code:: python

    host.fact.groups


Returns a list of groups on the system.



:code:`home`
~~~~~~~~~~~~

.. code:: python

    host.fact.home


Returns the home directory of the current user.



:code:`hostname`
~~~~~~~~~~~~~~~~

.. code:: python

    host.fact.hostname


Returns the current hostname of the server.



:code:`kernel_modules`
~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    host.fact.kernel_modules


Returns a dictionary of kernel module name -> info.

.. code:: python

    'module_name': {
        'size': 0,
        'instances': 0,
        'state': 'Live',
    },
    ...



:code:`linux_distribution`
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    host.fact.linux_distribution


Returns a dict of the Linux distribution version. Ubuntu, Debian, CentOS,
Fedora & Gentoo currently. Also contains any key/value items located in
release files.

.. code:: python

    {
        'name': 'CentOS',
        'major': 6,
        'minor': 5,
        'release_meta': {
            'DISTRIB_CODENAME': 'trusty',
            ...
        }
    }



:code:`linux_name`
~~~~~~~~~~~~~~~~~~

.. code:: python

    host.fact.linux_name


Returns the name of the Linux distribution. Shortcut for
``host.fact.linux_distribution['name']``.



:code:`lsb_release`
~~~~~~~~~~~~~~~~~~~

.. code:: python

    host.fact.lsb_release


Returns a dictionary of release information using ``lsb_release``.

.. code:: python

    {
        "id": "Ubuntu",
        "description": "Ubuntu 18.04.2 LTS",
        "release": "18.04",
        "codename": "bionic",
        ...
    }



:code:`mounts`
~~~~~~~~~~~~~~

.. code:: python

    host.fact.mounts


Returns a dictionary of mounted filesystems and information.

.. code:: python

    "/": {
        "device": "/dev/mv2",
        "type": "ext4",
        "options": [
            "rw",
            "relatime"
        ]
    },
    ...



:code:`os`
~~~~~~~~~~

.. code:: python

    host.fact.os


Returns the OS name according to ``uname``.



:code:`os_version`
~~~~~~~~~~~~~~~~~~

.. code:: python

    host.fact.os_version


Returns the OS version according to ``uname``.



:code:`sysctl`
~~~~~~~~~~~~~~

.. code:: python

    host.fact.sysctl


Returns a dictionary of sysctl settings and values.

.. code:: python

    {
        "fs.inotify.max_queued_events": 16384,
        "fs.inode-state": [
            44565,
            360,
        ],
        ...
    }



:code:`users`
~~~~~~~~~~~~~

.. code:: python

    host.fact.users


Returns a dictionary of users -> details.

.. code:: python

    'user_name': {
        'home': '/home/user_name',
        'shell': '/bin/bash,
        'group': 'main_user_group',
        'groups': [
            'other',
            'groups'
        ]
    },
    ...



:code:`which`
~~~~~~~~~~~~~

.. code:: python

    host.fact.which(name)


Returns the path of a given command, if available.


