Connectors Index
================

.. raw:: html

  <nav class="under-title-tabs">
    See also:
    <a href="operations.html">Operations Index</a>
    <a href="facts.html">Facts Index</a>
  </nav>

Connectors enable pyinfra to integrate with other tools out of the box. Connectors can do one of three things:

+ Implement how commands are executed (``@ssh``, ``@local``)
+ Generate inventory hosts and data (``@terraform`` and ``@vagrant``)
+ Both of the above (``@docker``)

Each connector page is listed below and contains examples as well as a list of available data that can be used to configure the connector.

**Want a new connector?** Check out :doc:`the writing connectors guide <./api/connectors>`.

.. raw:: html

   <h3>Popular connectors</h3>
   <div class="flex">

.. admonition:: :doc:`connectors/ssh`
   :class: note flex-half

   Connect to any SSH server.

.. admonition:: :doc:`connectors/docker`
   :class: note flex-half

   Create or modify Docker containers.

.. admonition:: :doc:`connectors/terraform`
   :class: note flex-half

   Get SSH targets from Terraform output.

.. admonition:: :doc:`connectors/local`
   :class: note flex-half

   Connect to the local machine running pyinfra.

.. raw:: html

   </div>
   <h3>All connectors</h3>

.. toctree::
   :maxdepth: 1
   :glob:

   connectors/*
