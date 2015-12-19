Init
----


Manages the state and configuration of init services.

:code:`init.d`
~~~~~~~~~~~~~~

Manage the state of /etc/init.d service scripts.

.. code:: python

    init.d(name, running=True, restarted=False, reloaded=False, command=None)


:code:`init.rc`
~~~~~~~~~~~~~~~

Manage the state of /etc/rc.d service scripts.

.. code:: python

    init.rc(name, running=True, restarted=False, reloaded=False, command=None)


:code:`init.service`
~~~~~~~~~~~~~~~~~~~~

Manage the state of "service" managed services.

.. code:: python

    init.service(name, running=True, restarted=False, reloaded=False, command=None)

