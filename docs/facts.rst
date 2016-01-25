Facts Index
===========

.. include:: _facts.rst


Apt
---

:code:`apt_sources`
~~~~~~~~~~~~~~~~~~~


    Returns a dict of installed apt sources:

    .. code:: python

        'http://archive.ubuntu.org': {
            'type': 'deb',
            'distribution': 'trusty',
            'components', ['main', 'multiverse']
        },
        ...
    


:code:`deb_package(name)`
~~~~~~~~~~~~~~~~~~~~~~~~~


    Returns information on a .deb file.
    


:code:`deb_packages`
~~~~~~~~~~~~~~~~~~~~


    Returns a dict of installed dpkg packages:

    .. code:: python

        'package_name': 'version',
        ...
    


Devices
-------

:code:`block_devices`
~~~~~~~~~~~~~~~~~~~~~


    Returns a dict of (mounted) block devices:

    .. code:: python

        '/dev/sda1': {
            'available': '39489508',
            'used_percent': '3',
            'mount': '/',
            'used': '836392',
            'blocks': '40325900'
        },
        ...
    


:code:`network_devices`
~~~~~~~~~~~~~~~~~~~~~~~


    Gets & returns a dict of network devices:

    .. code:: python

        'eth0': {
            'ipv4': {
                'address': '127.0.0.1',
                'netmask': '255.255.255.255',
                'broadcast': '127.0.0.13'
            },
            'ipv6': {
                'size': '64',
                'address': 'fe80::a00:27ff:fec3:36f0'
            }
        },
        ...
    


Files
-----

:code:`directory(name)`
~~~~~~~~~~~~~~~~~~~~~~~


:code:`file(name)`
~~~~~~~~~~~~~~~~~~


:code:`find_files(name)`
~~~~~~~~~~~~~~~~~~~~~~~~

Returns a list of files/dirs from a start point, recursively using find.


:code:`find_in_file(name)`
~~~~~~~~~~~~~~~~~~~~~~~~~~

Checks for the existence of text in a file using grep.


:code:`sha1_file(name)`
~~~~~~~~~~~~~~~~~~~~~~~

Returns a SHA1 hash of a file. Works with both sha1sum and sha1.


Gem
---

:code:`gem_packages`
~~~~~~~~~~~~~~~~~~~~


    Returns a dict of installed gem packages:

    .. code:: python

        'package_name': 'version',
        ...
    


Git
---

:code:`git_branch(name)`
~~~~~~~~~~~~~~~~~~~~~~~~


Init
----

:code:`initd_status`
~~~~~~~~~~~~~~~~~~~~


    Low level check for every /etc/init.d/* script. Unfortunately many of these mishehave and return
    exit status 0 while also displaying the help info/not offering status support.

    Returns a dict of name -> status.

    Expected codes found at:
        http://refspecs.linuxbase.org/LSB_3.1.0/LSB-Core-generic/LSB-Core-generic/iniscrptact.html
    


:code:`rcd_status`
~~~~~~~~~~~~~~~~~~


    As above but for BSD (/etc/rc.d) systems. Unlike Linux/init.d, BSD init scripts are
    well behaved and as such their output can be trusted.
    


:code:`service_status`
~~~~~~~~~~~~~~~~~~~~~~

Returns a dict of name -> status for services listed by "service".


:code:`systemctl_status`
~~~~~~~~~~~~~~~~~~~~~~~~

Returns a dict of name -> status for systemd managed services.


Npm
---

:code:`npm_local_packages(directory)`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


    Returns a dict of locally installed npm packages in a given directory:

    .. code:: python

        'package_name': 'version',
        ...
    


:code:`npm_packages`
~~~~~~~~~~~~~~~~~~~~


    Returns a dict of globally installed npm packages:

    .. code:: python

        'package_name': 'version',
        ...
    


Pip
---

:code:`pip_packages`
~~~~~~~~~~~~~~~~~~~~


    Returns a dict of installed pip packages:

    .. code:: python

        'package_name': 'version',
        ...
    


:code:`pip_packages_virtualenv(venv)`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Pkg
---

:code:`pkg_packages`
~~~~~~~~~~~~~~~~~~~~


    Returns a dict of installed pkg packages:

    .. code:: python

        'package_name': 'version',
        ...
    


Server
------

:code:`arch`
~~~~~~~~~~~~


:code:`date`
~~~~~~~~~~~~

Returns the current datetime on the server.


:code:`home`
~~~~~~~~~~~~


:code:`hostname`
~~~~~~~~~~~~~~~~


:code:`linux_distribution`
~~~~~~~~~~~~~~~~~~~~~~~~~~


    Returns a dict of the Linux distribution version. Ubuntu, CentOS & Debian currently:

    .. code:: python

        {
            'name': 'CentOS',
            'major': 6,
            'minor': 5
        }
    


:code:`os`
~~~~~~~~~~


:code:`os_version`
~~~~~~~~~~~~~~~~~~


:code:`users`
~~~~~~~~~~~~~


    Gets & returns a dict of users -> details:

    .. code:: python

        'user_name': {
            'uid': 1,
            'gid': 1,
            'home': '/home/user_name',
            'shell': '/bin/bash
        },
        ...
    


Yum
---

:code:`rpm_packages`
~~~~~~~~~~~~~~~~~~~~


    Returns a dict of installed rpm packages:

    .. code:: python

        'package_name': 'version',
        ...
    


:code:`rpm_package(name)`
~~~~~~~~~~~~~~~~~~~~~~~~~


    Returns information on a .rpm file.