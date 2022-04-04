Connectors Index
================

Connectors enable ``pyinfra`` to integrate with other tools out of the box. Connectors can do one of three things:

+ Implement how commands are executed (``@ssh``, ``@local``)
+ Generate inventory hosts and data (``@terraform`` and ``@vagrant``)
+ Both of the above (``@docker``)

Each connector page is listed below and contains examples as well as a list of available data that can be used to configure the connector.

**Want a new connector?** Check out :doc:`the writing connectors guide <./api/connectors>`.

.. toctree::
   :maxdepth: 1
   :glob:

   connectors/*
`