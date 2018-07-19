Facts Index
===========

.. include:: facts_.rst


Files
-----

:code:`directory(name)`
~~~~~~~~~~~~~~~~~~~~~~~


:code:`file(name)`
~~~~~~~~~~~~~~~~~~


:code:`find_directories(name)`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


    Returns a list of directories from a start point, recursively using find.
    


:code:`find_files(name)`
~~~~~~~~~~~~~~~~~~~~~~~~


    Returns a list of files from a start point, recursively using find.
    


:code:`find_in_file(name, pattern)`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


    Checks for the existence of text in a file using grep. Returns a list of matching
    lines if the file exists, and ``None`` if the file does not.
    


:code:`find_links(name)`
~~~~~~~~~~~~~~~~~~~~~~~~


    Returns a list of links from a start point, recursively using find.
    


:code:`link(name)`
~~~~~~~~~~~~~~~~~~


:code:`sha1_file(name)`
~~~~~~~~~~~~~~~~~~~~~~~


    Returns a SHA1 hash of a file. Works with both sha1sum and sha1.
    


:code:`socket(name)`
~~~~~~~~~~~~~~~~~~~~


Git
---

:code:`git_branch(name)`
~~~~~~~~~~~~~~~~~~~~~~~~


Server
------

:code:`arch`
~~~~~~~~~~~~


:code:`command`
~~~~~~~~~~~~~~~


:code:`crontab`
~~~~~~~~~~~~~~~


    Returns a dict of cron command -> execution time.

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


    Returns the current datetime on the server.
    


:code:`groups`
~~~~~~~~~~~~~~


    Returns a list of groups on the system.
    


:code:`home`
~~~~~~~~~~~~


:code:`hostname`
~~~~~~~~~~~~~~~~


:code:`kernel_modules`
~~~~~~~~~~~~~~~~~~~~~~


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


:code:`sysctl`
~~~~~~~~~~~~~~


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


Docker
------

:code:`docker_containers`
~~~~~~~~~~~~~~~~~~~~~~~~~


    Returns a list of all Docker containers.
    


:code:`docker_fact_base`
~~~~~~~~~~~~~~~~~~~~~~~~


:code:`docker_images`
~~~~~~~~~~~~~~~~~~~~~


    Returns a list of all Docker images.
    


:code:`docker_networks`
~~~~~~~~~~~~~~~~~~~~~~~


    Returns a list of all Docker networks.
    


Npm
---

:code:`npm_packages(directory)`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


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
    


:code:`rpm_package(name)`
~~~~~~~~~~~~~~~~~~~~~~~~~


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
    


:code:`deb_package(name)`
~~~~~~~~~~~~~~~~~~~~~~~~~


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

:code:`ip6tables_chains(table)`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


    Returns a dict of ip6tables chains & policies:

    .. code:: python

        'NAME': 'POLICY',
        ...
    


:code:`ip6tables_rules(table)`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


    Returns a list of ip6tables rules for a specific table:

    .. code:: python

        {
            'chain': 'PREROUTING',
            'jump': 'DNAT'
        },
        ...
    


:code:`iptables_chains(table)`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


    Returns a dict of iptables chains & policies:

    .. code:: python

        'NAME': 'POLICY',
        ...
    


:code:`iptables_rules(table)`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


    Returns a list of iptables rules for a specific table:

    .. code:: python

        {
            'chain': 'PREROUTING',
            'jump': 'DNAT'
        },
        ...
    


Pip
---

:code:`pip_packages(pip)`
~~~~~~~~~~~~~~~~~~~~~~~~~


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
    


:code:`launchd_status`
~~~~~~~~~~~~~~~~~~~~~~


    Returns a dict of name -> status for launchd managed services.
    


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
    


Mysql
-----

:code:`mysql_databases(mysql_user, mysql_password, mysql_host, mysql_port)`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


    Returns a list of existing MySQL databases.
    


:code:`mysql_fact_base(mysql_user, mysql_password, mysql_host, mysql_port)`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


:code:`mysql_user_grants(user, hostname, mysql_user, mysql_password, mysql_host, mysql_port)`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


:code:`mysql_users(mysql_user, mysql_password, mysql_host, mysql_port)`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


    Returns a dict of MySQL user@host's and their associated data:

    .. code:: python

        'user@host': {
            'permissions': ['Alter', 'Grant'],
            'max_connections': 5,
            ...
        },
        ...