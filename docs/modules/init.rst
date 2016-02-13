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

    init.d(
        name, running=True, restarted=False, reloaded=False,
        command=None, enabled=None, priority=20, start_runlevels=(2, 3, 4, 5), kill_runlevels=(0, 1, 6)
    )

+ **name**: name of the service to manage
+ **running**: whether the service should be running
+ **restarted**: whether the service should be restarted
+ **reloaded**: whether the service should be reloaded
+ **command**: custom command to pass like: ``/etc/init.d/<name> <command>``
+ **enabled**: whether this service should be enabled/disabled at runlevels
+ **priority**: priority to execute the service
+ **start_runlevels**: which runlevels should the service run when enabled
+ **kill_runlevels**: which runlevels should the service stop when enabled

Enabled, priority & runlevels:
    When enabled is ``True`` both priority and runlevels decide which links to init
    scripts are pushed into ``/etc/rcX.d`` where X is the runlevel. When enabled is
    ``False`` pyinfra removes any links matching the service name from all
    ``/etc/rcX.d`` directories.


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

