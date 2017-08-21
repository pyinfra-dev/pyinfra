Vzctl
-----


Manage OpenVZ containers with ``vzctl``.

:code:`vzctl.create`
~~~~~~~~~~~~~~~~~~~~

Create OpenVZ containers.

.. code:: python

    vzctl.create(ctid, template=None)

+ **ctid**: CTID of the container to create


:code:`vzctl.delete`
~~~~~~~~~~~~~~~~~~~~

Delete OpenVZ containers.

.. code:: python

    vzctl.delete(ctid)

+ **ctid**: CTID of the container to delete


:code:`vzctl.mount`
~~~~~~~~~~~~~~~~~~~

Mount OpenVZ container filesystems.

.. code:: python

    vzctl.mount(ctid)

+ **ctid**: CTID of the container to mount


:code:`vzctl.restart`
~~~~~~~~~~~~~~~~~~~~~

Restart OpenVZ containers.

.. code:: python

    vzctl.restart(ctid, force=False)

+ **ctid**: CTID of the container to restart
+ **force**: whether to force container start


:code:`vzctl.set`
~~~~~~~~~~~~~~~~~

Set OpenVZ container details.

.. code:: python

    vzctl.set(ctid, save=True)

+ **ctid**: CTID of the container to set
+ **save**: whether to save the changes
+ **settings**: settings/arguments to apply to the container

Settings/arguments:
    these are mapped directly to ``vztctl`` arguments, eg
    ``hostname='my-host.net'`` becomes ``--hostname my-host.net``.


:code:`vzctl.start`
~~~~~~~~~~~~~~~~~~~

Start OpenVZ containers.

.. code:: python

    vzctl.start(ctid, force=False)

+ **ctid**: CTID of the container to start
+ **force**: whether to force container start


:code:`vzctl.stop`
~~~~~~~~~~~~~~~~~~

Stop OpenVZ containers.

.. code:: python

    vzctl.stop(ctid)

+ **ctid**: CTID of the container to stop


:code:`vzctl.unmount`
~~~~~~~~~~~~~~~~~~~~~

Unmount OpenVZ container filesystems.

.. code:: python

    vzctl.unmount(ctid)

+ **ctid**: CTID of the container to unmount

