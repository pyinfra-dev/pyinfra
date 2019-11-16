Init
----

:code:`initd_status`
~~~~~~~~~~~~~~~~~~~~

.. code:: python

    host.fact.initd_status


Low level check for every /etc/init.d/* script. Unfortunately many of these
mishehave and return exit status 0 while also displaying the help info/not
offering status support.

Returns a dict of name -> status.

Expected codes found at:
    http://refspecs.linuxbase.org/LSB_3.1.0/LSB-Core-generic/LSB-Core-generic/iniscrptact.html



:code:`launchd_status`
~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    host.fact.launchd_status


Returns a dict of name -> status for launchd managed services.



:code:`rcd_status`
~~~~~~~~~~~~~~~~~~

.. code:: python

    host.fact.rcd_status


Same as ``initd_status`` but for BSD (/etc/rc.d) systems. Unlike Linux/init.d,
BSD init scripts are well behaved and as such their output can be trusted.



:code:`systemd_enabled`
~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    host.fact.systemd_enabled


Returns a dict of name -> whether enabled for systemd managed services.



:code:`systemd_status`
~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    host.fact.systemd_status


Returns a dict of name -> status for systemd managed services.



:code:`upstart_status`
~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    host.fact.upstart_status


Returns a dict of name -> status for upstart managed services.


