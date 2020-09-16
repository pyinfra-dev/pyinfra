pyinfra Documentation
=========================

Welcome to the ``pyinfra`` v1 documentation. If you're new to ``pyinfra`` you should start with the :doc:`getting started <./getting_started>` page.

.. Important::
    This is the documentation for ``pyinfra`` **v1**, it is highly recommended to use this version!

    If you're upgrading from ``0.x`` see `the 0->1 upgrade notes <compatibility.html#upgrading-pyinfra-from-0-x-1-x>`_.


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
        A list of all facts ``pyinfra`` can gather from hosts, e.g. ``host.fact.os``.

.. compound::
    :doc:`examples`
        A set of documented example deploys highlighting common patterns.

.. compound::
    :doc:`connectors`
        Connectors allow ``pyinfra`` to seamlessly integrate with other tools.


How pyinfra Works
-----------------

.. compound::
    :doc:`deploy_process`
        Learn how ``pyinfra`` executes operations.

.. compound::
    :doc:`api/index`
        Discover the ``pyinfra`` Python API.

.. compound::
    :doc:`api/operations`
        Learn how to write your own operations for ``pyinfra``.

.. compound::
    :doc:`api/facts`
        Learn how to write your own facts for ``pyinfra``.


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
    examples
    connectors

.. toctree::
    :hidden:
    :caption: How pyinfra Works

    deploy_process
    api/index
    api/operations
    api/facts

.. toctree::
    :hidden:
    :caption: Meta

    api/reference
    performance
    compatibility
    contributing

.. toctree::
    :hidden:
    :caption: Elsewhere

    pyinfra.com <https://pyinfra.com>
    pyinfra on GitHub <https://github.com/Fizzadar/pyinfra>
