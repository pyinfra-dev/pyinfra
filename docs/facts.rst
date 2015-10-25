Facts Index
===========

.. include:: _facts.rst


Devices
-------

:code:`block_devices`
~~~~~~~~~~~~~~~~~~~~~

Returns a dict of (mounted) block devices -> details.


Files
-----

:code:`directory(name)`
~~~~~~~~~~~~~~~~~~~~~~~


:code:`file(name)`
~~~~~~~~~~~~~~~~~~


:code:`find_files(name)`
~~~~~~~~~~~~~~~~~~~~~~~~

Returns a list of files/dirs from a start point, recursively using find.


:code:`sha1_file(name)`
~~~~~~~~~~~~~~~~~~~~~~~

Returns a SHA1 hash of a file. Works with both sha1sum and sha1.


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

As above but for BSD (/etc/rc.d) systems. Unlike Linux/init.d, BSD init scripts are well behaved
and as such their output can be trusted.



:code:`service_status`
~~~~~~~~~~~~~~~~~~~~~~

Returns a dict of name -> status for services listed by "service".


:code:`systemctl_status`
~~~~~~~~~~~~~~~~~~~~~~~~

Returns a dict of name -> status for systemd managed services.


Mysql
-----

:code:`mysql_databases`
~~~~~~~~~~~~~~~~~~~~~~~


:code:`mysql_users`
~~~~~~~~~~~~~~~~~~~


Packages
--------

:code:`deb_packages`
~~~~~~~~~~~~~~~~~~~~

Returns a dict of installed dpkg packages -> version.


:code:`pip_packages`
~~~~~~~~~~~~~~~~~~~~

Returns a dict of installed pip packages -> version.


:code:`pip_packages_venv(venv)`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


:code:`pkg_packages`
~~~~~~~~~~~~~~~~~~~~

Returns a dict of installed pkg packages -> version.


:code:`rpm_packages`
~~~~~~~~~~~~~~~~~~~~

Returns a dict of installed rpm packages -> version.


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

Returns the Linux distribution. Ubuntu, CentOS & Debian currently.


:code:`os`
~~~~~~~~~~


:code:`os_version`
~~~~~~~~~~~~~~~~~~


:code:`users`
~~~~~~~~~~~~~

Gets & returns a dict of users -> details.