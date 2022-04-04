.. meta::
    :description: pyinfra documentation
    :keywords: pyinfra, documentation


pyinfra Documentation
=========================

Welcome to the ``pyinfra`` v2 documentation. If you're new to ``pyinfra`` you should start with the :doc:`getting started <./getting_started>` page.


Using pyinfra
-------------

.. compound::
    :doc:`getting-started`
        A quickstart guide introducing the basics of ``pyinfra``. Start here!

.. compound::
    :doc:`using-operations`
        The guide to writing reusable, committable operations in Python files.

.. compound::
    :doc:`inventory-data`
        Use groups, host, and group data to control and configure operations for any environment.

.. compound::
    :doc:`arguments`
        Arguments available in all operations & facts such as ``_sudo``, ``_serial`` and ``_env``.

.. compound::
    :doc:`cli`
        The ``pyinfra`` CLI is extremely powerful for ad hoc command execution and management.


Deploy Reference
----------------

.. compound::
    :doc:`examples`
        A set of documented example deploys that focus on common patterns and use-cases.

.. compound::
    :doc:`connectors`
        A list of connectors to target different hosts such as ``@docker``, ``@local`` and ``@terraform``.

.. compound::
    :doc:`operations`
        A list of all available operations and their arguments, e.g. ``apt.packages``.

.. compound::
    :doc:`facts`
        A list of all facts ``pyinfra`` can gather from hosts, e.g. ``server.Hostname``.


How pyinfra Works
-----------------

.. compound::
    :doc:`api/deploys`
        How to package, redistribute and share ``pyinfra`` deploys as Python packages.

.. compound::
    :doc:`api/connectors`
        Learn how to write your own connectors for ``pyinfra``.

.. compound::
    :doc:`api/operations`
        Learn how to write your own operations for ``pyinfra``.

.. compound::
    :doc:`api/facts`
        Learn how to write your own facts for ``pyinfra``.

.. compound::
    :doc:`deploy-process`
        Learn how ``pyinfra`` executes operations against target hosts.


.. toctree::
    :hidden:
    :caption: Using pyinfra

    getting-started
    using-operations
    inventory-data
    arguments
    cli

.. toctree::
    :hidden:
    :maxdepth: 1
    :caption: Deploy Reference

    examples
    connectors
    operations
    facts

.. toctree::
    :hidden:
    :caption: How pyinfra Works

    api/deploys
    api/connectors
    api/operations
    api/facts
    deploy-process

.. toctree::
    :hidden:
    :caption: Meta

    support
    contributing
    compatibility
    performance
    api/reference
