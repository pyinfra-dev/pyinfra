Facts Index
===========

.. include:: facts_.rst


Files
-----

:code:`directory`
~~~~~~~~~~~~~~~~~


:code:`file`
~~~~~~~~~~~~


:code:`find_directories`
~~~~~~~~~~~~~~~~~~~~~~~~


    Returns a list of directories from a start point, recursively using find.
    


:code:`find_files`
~~~~~~~~~~~~~~~~~~


    Returns a list of files from a start point, recursively using find.
    


:code:`find_in_file`
~~~~~~~~~~~~~~~~~~~~


    Checks for the existence of text in a file using grep. Returns a list of matching
    lines if the file exists, and ``None`` if the file does not.
    


:code:`find_links`
~~~~~~~~~~~~~~~~~~


    Returns a list of links from a start point, recursively using find.
    


:code:`link`
~~~~~~~~~~~~


:code:`sha1_file`
~~~~~~~~~~~~~~~~~


    Returns a SHA1 hash of a file. Works with both sha1sum and sha1.
    


:code:`socket`
~~~~~~~~~~~~~~


Git
---

:code:`git_branch`
~~~~~~~~~~~~~~~~~~


Server
------

:code:`arch`
~~~~~~~~~~~~


:code:`command`
~~~~~~~~~~~~~~~


:code:`date`
~~~~~~~~~~~~


    Returns the current datetime on the server.
    


:code:`groups`
~~~~~~~~~~~~~~


    Returns a list of groups on the system.
    


:code:`home`
~~~~~~~~~~~~


:code:`hostname`
~~~~~~~~~~~~~~~~


:code:`linux_distribution`
~~~~~~~~~~~~~~~~~~~~~~~~~~


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
    


:code:`lsb_release`
~~~~~~~~~~~~~~~~~~~


:code:`os`
~~~~~~~~~~


:code:`os_version`
~~~~~~~~~~~~~~~~~~


:code:`users`
~~~~~~~~~~~~~


    Returns a dict of users -> details:

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


Npm
---

:code:`npm_packages`
~~~~~~~~~~~~~~~~~~~~


    Returns a dict of installed npm packages globally or in a given directory:

    .. code:: python

        'package_name': 'version',
        ...
    


Yum
---

:code:`rpm_packages`
~~~~~~~~~~~~~~~~~~~~


    Returns a dict of installed rpm packages:

    .. code:: python

        'package_name': 'version',
        ...
    


:code:`rpm_package`
~~~~~~~~~~~~~~~~~~~


    Returns information on a .rpm file:

    .. code:: python

        {
            'name': 'my_package',
            'version': '1.0.0'
        }
    


Vzctl
-----

:code:`openvz_containers`
~~~~~~~~~~~~~~~~~~~~~~~~~


    Returns a dict of running OpenVZ containers by CTID:

    .. code:: python

        {
            666: {
                'ip': [],
                'ostemplate': 'ubuntu...',
                ...
            },
            ...
        }
    


Apt
---

:code:`apt_sources`
~~~~~~~~~~~~~~~~~~~


    Returns a list of installed apt sources:

    .. code:: python

        {
            'type': 'deb',
            'url': 'http://archive.ubuntu.org',
            'distribution': 'trusty',
            'components', ['main', 'multiverse']
        },
        ...
    


:code:`deb_package`
~~~~~~~~~~~~~~~~~~~


    Returns information on a .deb file.
    


:code:`deb_packages`
~~~~~~~~~~~~~~~~~~~~


    Returns a dict of installed dpkg packages:

    .. code:: python

        'package_name': 'version',
        ...
    


Hardware
--------

:code:`cpus`
~~~~~~~~~~~~


    Returns the number of CPUs on this server.
    


:code:`memory`
~~~~~~~~~~~~~~


    Returns the memory installed in this server, in MB.
    


Pkg
---

:code:`pkg_packages`
~~~~~~~~~~~~~~~~~~~~


    Returns a dict of installed pkg packages:

    .. code:: python

        'package_name': 'version',
        ...
    


Iptables
--------

:code:`ip6tables_chains`
~~~~~~~~~~~~~~~~~~~~~~~~


    Returns a dict of ip6tables chains & policies:

    .. code:: python

        'NAME': 'POLICY',
        ...
    


:code:`ip6tables_rules`
~~~~~~~~~~~~~~~~~~~~~~~


    Returns a list of ip6tables rules for a specific table:

    .. code:: python

        {
            'chain': 'PREROUTING',
            'jump': 'DNAT'
        },
        ...
    


:code:`iptables_chains`
~~~~~~~~~~~~~~~~~~~~~~~


    Returns a dict of iptables chains & policies:

    .. code:: python

        'NAME': 'POLICY',
        ...
    


:code:`iptables_rules`
~~~~~~~~~~~~~~~~~~~~~~


    Returns a list of iptables rules for a specific table:

    .. code:: python

        {
            'chain': 'PREROUTING',
            'jump': 'DNAT'
        },
        ...
    


Pip
---

:code:`pip_packages`
~~~~~~~~~~~~~~~~~~~~


    Returns a dict of installed pip packages:

    .. code:: python

        'package_name': 'version',
        ...
    


Init
----

:code:`initd_status`
~~~~~~~~~~~~~~~~~~~~


    Low level check for every /etc/init.d/* script. Unfortunately many of these
    mishehave and return exit status 0 while also displaying the help info/not
    offering status support.

    Returns a dict of name -> status.

    Expected codes found at:
        http://refspecs.linuxbase.org/LSB_3.1.0/LSB-Core-generic/LSB-Core-generic/iniscrptact.html
    


:code:`rcd_enabled`
~~~~~~~~~~~~~~~~~~~


    Returns a dict of service name -> whether enabled (on boot) status. Different
    to Linux variants because BSD has no/one runlevel.
    


:code:`rcd_status`
~~~~~~~~~~~~~~~~~~


    Same as ``initd_status`` but for BSD (/etc/rc.d) systems. Unlike Linux/init.d,
    BSD init scripts are well behaved and as such their output can be trusted.
    


:code:`systemd_enabled`
~~~~~~~~~~~~~~~~~~~~~~~


    Returns a dict of name -> whether enabled for systemd managed services.
    


:code:`systemd_status`
~~~~~~~~~~~~~~~~~~~~~~


    Returns a dict of name -> status for systemd managed services.
    


:code:`upstart_status`
~~~~~~~~~~~~~~~~~~~~~~


    Returns a dict of name -> status for upstart managed services.
    


Gem
---

:code:`gem_packages`
~~~~~~~~~~~~~~~~~~~~


    Returns a dict of installed gem packages:

    .. code:: python

        'package_name': 'version',
        ...
    


Lxd
---

:code:`lxd_containers`
~~~~~~~~~~~~~~~~~~~~~~


    Returns a list of running LXD containers
    


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