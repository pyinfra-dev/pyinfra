.. meta::
    :description: Documentation for pyinfra
    :keywords: pyinfra, documentation, configuration, management, infrastructure


pyinfra Documentation
=========================

Welcome to the pyinfra v3 documentation. If you're new to pyinfra you should start with the :doc:`getting-started` page.


Using pyinfra
-------------

.. compound::
    :doc:`getting-started`
        Start here! The quickest way to learn the basics of pyinfra and get started.

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
        The pyinfra CLI is extremely powerful for ad hoc command execution and management.

.. compound::
    :doc:`faq`
        Quick answers to the most commonly asked questions for using pyinfra.


Deploy Reference
----------------

.. compound::
    :doc:`operations`
        A list of all available operations and their arguments, e.g. ``apt.packages``.

.. compound::
    :doc:`facts`
        A list of all facts pyinfra can gather from hosts, e.g. ``server.Hostname``.

.. compound::
    :doc:`connectors`
        A list of connectors to target different hosts such as ``@docker``, ``@local`` and ``@terraform``.


How pyinfra Works
-----------------

.. compound::
    :doc:`deploy-process`
        Discover how pyinfra orders, diffs and executes operations against target hosts.

.. compound::
    :doc:`api/deploys`
        How to package, redistribute and share pyinfra deploys as Python packages.

.. compound::
    :doc:`api/connectors`
        How to write your own connectors for pyinfra.

.. compound::
    :doc:`api/operations`
        How to write your own operations for pyinfra.

.. compound::
    :doc:`api/facts`
        How to write your own facts for pyinfra.

.. compound::
    :doc:`api/index`
        How to use the pyinfra API.


.. toctree::
    :hidden:
    :caption: Using pyinfra

    getting-started
    using-operations
    inventory-data
    arguments
    cli
    faq

.. toctree::
    :hidden:
    :maxdepth: 1
    :caption: Deploy Reference

    operations
    facts
    connectors

.. toctree::
    :hidden:
    :caption: How pyinfra Works

    deploy-process
    api/deploys
    api/operations
    api/facts
    api/connectors
    api/index

.. toctree::
    :hidden:
    :caption: Meta

    support
    contributing
    compatibility
    performance
    changes
    api/reference
