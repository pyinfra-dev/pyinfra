pyinfra Documentation
=====================

Welcome to the pyinfra documentation; it is split into two sections - how to use pyinfra and the references. If you're new to pyinfra you should start with the :doc:`getting started <./getting_started>` page.


Using pyinfra
-------------

.. compound::
    :doc:`getting_started`
        A quickstart guide introducing the basics of pyinfra. Start here!

.. compound::
    :doc:`deploys`
        The definitive guide to writing reusable, committable deploys (think plays/workflows/playbooks).

.. compound::
    :doc:`cli`
        The pyinfra CLI is extremely powerful for ad hoc command execution and management.

.. compound::
    :doc:`connectors`
        Connectors allow pyinfra to seamlessly integrate with other tools.


Deploy Reference
----------------

.. compound::
    :doc:`operations`
        A list of all available operations and their arguments, eg ``apt.packages``.

.. compound::
    :doc:`facts`
        A list of all facts pyinfra can gather from hosts, eg ``host.fact.os``.

.. compound::
    :doc:`examples`
        A set of documented example deploys highlighting common patterns.


.. toctree::
    :hidden:
    :caption: Using pyinfra

    getting_started
    deploys
    cli
    connectors

.. toctree::
    :hidden:
    :maxdepth: 1
    :caption: Deploy Reference

    operations
    facts
    examples

.. toctree::
    :hidden:
    :caption: pyinfra API

    api/modules
    api/deploys
    api/example
    api/reference

.. toctree::
    :hidden:
    :caption: How pyinfra Works

    deploy_process
    performance
    compatibility

.. toctree::
    :hidden:
    :caption: Elsewhere

    pyinfra.com <https://pyinfra.com>
    pyinfra on GitHub <https://github.com/Fizzadar/pyinfra>
