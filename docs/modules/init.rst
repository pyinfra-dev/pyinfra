Init
----


Manages the state and configuration of init services. Support for:

+ SysVinit (/etc/init.d)
+ BSD init (/etc/rc.d)
+ Upstart
+ Systemctl

:code:`init.d`
~~~~~~~~~~~~~~

Manage the state of SysV Init (/etc/init.d) service scripts.

.. code:: python

    init.d(name, running=True, restarted=False, reloaded=False, enabled=None, command=None)

+ **name**: name of the service to manage
+ **running**: whether the service should be running
+ **restarted**: whether the service should be restarted
+ **reloaded**: whether the service should be reloaded
+ **enabled**: whether this service should be enabled/disabled
+ **command**: command (eg. reload) to run like: ``/etc/init.d/<name> <command>``

Enabled:
    Because managing /etc/rc.d/X files is a mess, only certain Linux distributions
    support enabling/disabling services:

    + Ubuntu/Debian (``update-rc.d``)
    + CentOS/Fedora/RHEL (``chkconfig``)
    + Gentoo (``rc-update``)

    For other distributions and more granular service control, see the
    ``init.d_enable`` operation.


:code:`init.d_enable`
~~~~~~~~~~~~~~~~~~~~~

Manually enable /etc/init.d scripts by creating /etc/rcX.d/Y links.

.. code:: python

    init.d_enable(
        name, start_priority=20, stop_priority=80, start_levels=(2, 3, 4, 5),
        stop_levels=(0, 1, 6)
    )

+ **name**: name of the service to enable
+ **start_priority**: priority to start the service
+ **stop_priority**: priority to stop the service
+ **start_levels**: which runlevels should the service run when enabled
+ **stop_levels**: which runlevels should the service stop when enabled


:code:`init.rc`
~~~~~~~~~~~~~~~

Manage the state of BSD init (/etc/rc.d) service scripts.

.. code:: python

    init.rc(name, running=True, restarted=False, reloaded=False, command=None, enabled=None)

+ **name**: name of the service to manage
+ **running**: whether the service should be running
+ **restarted**: whether the service should be restarted
+ **reloaded**: whether the service should be reloaded
+ **command**: custom command to pass like: ``/etc/rc.d/<name> <command>``
+ **enabled**: whether this service should be enabled/disabled on boot


:code:`init.systemd`
~~~~~~~~~~~~~~~~~~~~

Manage the state of systemd managed services.

.. code:: python

    init.systemd(
        name, running=True, restarted=False, reloaded=False, command=None, enabled=None,
        daemon_reload=False
    )

+ **name**: name of the service to manage
+ **running**: whether the service should be running
+ **restarted**: whether the service should be restarted
+ **reloaded**: whether the service should be reloaded
+ **command**: custom command to pass like: ``/etc/rc.d/<name> <command>``
+ **enabled**: whether this service should be enabled/disabled on boot
+ **daemon_reload**: reload the systemd daemon to read updated unit files


:code:`init.upstart`
~~~~~~~~~~~~~~~~~~~~

Manage the state of upstart managed services.

.. code:: python

    init.upstart(name, running=True, restarted=False, reloaded=False, command=None, enabled=None)

+ **name**: name of the service to manage
+ **running**: whether the service should be running
+ **restarted**: whether the service should be restarted
+ **reloaded**: whether the service should be reloaded
+ **command**: custom command to pass like: ``/etc/rc.d/<name> <command>``
+ **enabled**: whether this service should be enabled/disabled on boot

Enabling/disabling services:
    Upstart jobs define runlevels in their config files - as such there is no way to
    edit/list these without fiddling with the config. So pyinfra simply manages the
    existence of a ``/etc/init/<service>.override`` file, and sets its content to
    "manual" to disable automatic start of services.

