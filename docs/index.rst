.. meta::
    :description: pyinfra documentation
    :keywords: pyinfra, documentation


pyinfra Documentation
=========================

Welcome to the ``pyinfra`` v1 documentation. If you're new to ``pyinfra`` you should start with the :doc:`getting started <./getting_started>` page.


Using pyinfra
-------------

.. compound::
    :doc:`getting_started`
        A quickstart guide introducing the basics of ``pyinfra``. Start here!

.. compound::
    :doc:`deploys`
        The definitive guide to writing reusable, committable deploys (think plays/workflows/playbooks).

.. compound::
    :doc:`cli`
        The ``pyinfra`` CLI is extremely powerful for ad hoc command execution and management.

.. compound::
    :doc:`api/deploys`
        How to package, redistribute and share ``pyinfra`` deploys as Python packages.


Deploy Reference
----------------

.. compound::
    :doc:`operations`
        A list of all available operations and their arguments, e.g. ``apt.packages``.

.. compound::
    :doc:`facts`
        A list of all facts (data) ``pyinfra`` can gather from hosts, e.g. ``server.Hostname``.

.. compound::
    :doc:`arguments`
        Arguments available in all operations & facts such as ``_sudo``, ``_serial`` and ``_env``.

.. compound::
    :doc:`connectors`
        Connectors deploy to different target hosts such as ``SSH``, ``Docker`` and local.

.. compound::
    :doc:`examples`
        A set of documented example deploys that focus on common patterns and use-cases.


How pyinfra Works
-----------------

.. compound::
    :doc:`deploy_process`
        Learn how ``pyinfra`` executes operations against target hosts.

.. compound::
    :doc:`api/connectors`
        Build connectors to integrate ``pyinfra`` with other systems/tools/targets.

.. compound::
    :doc:`api/operations`
        Learn how to write your own operations for ``pyinfra``.

.. compound::
    :doc:`api/facts`
        Learn how to write your own facts for ``pyinfra``.

.. compound::
    :doc:`api/index`
        Discover the ``pyinfra`` Python API.

.. compound::
    :doc:`api/reference`
        Explore the ``pyinfra`` Python API.


.. toctree::
    :hidden:
    :caption: Using pyinfra

    getting_started
    deploys
    cli
    api/deploys

.. toctree::
    :hidden:
    :maxdepth: 1
    :caption: Deploy Reference

    operations
    facts
    arguments
    connectors
    examples

.. toctree::
    :hidden:
    :caption: How pyinfra Works

    deploy_process
    api/operations
    api/facts
    api/connectors
    api/index
    api/reference

.. toctree::
    :hidden:
    :caption: Meta

    support
    contributing
    compatibility
    performance
