pyinfra Documentation
=====================

pyinfra is designed to automate/provision/manage/deploy servers at scale.

It can be used for ad-hoc command execution, service deployment, configuration management; you could say that pyinfra is like a combination of Ansible + Fabric. It is asynchronous, highly performant and can target thousands of hosts in parallel. It is entirely configured in Python, allowing for near-infinite extendability out of the box.

.. compound::
    :doc:`getting_started`
        A quickstart guide introducing the basics of pyinfra. Start here!

.. compound::
    :doc:`deploys`
        The definitive guide to building a deploy with pyinfra.

.. compound::
    :doc:`examples`
        A set of documented example deploys highlighting common patterns.

.. compound::
    :doc:`connectors`
        Connectors allow pyinfra to seamlessly integrate with other tools.

Reference
---------

.. compound::
    :doc:`operations`
        A list of all available operations and their arguments, eg ``apt.packages``.

.. compound::
    :doc:`facts`
        A list of all facts pyinfra can gather from hosts, eg ``host.fact.os``.


.. toctree::
    :hidden:
    :maxdepth: 1
    :caption: Using pyinfra

    getting_started
    deploys
    examples
    connectors

.. toctree::
    :hidden:
    :maxdepth: 1
    :caption: Deploy Reference

    operations
    facts

.. toctree::
    :hidden:
    :maxdepth: 1
    :caption: pyinfra API

    api/modules
    api/deploys
    api/example
    api/reference

.. toctree::
    :hidden:
    :maxdepth: 1
    :caption: How pyinfra Works

    deploy_process
    performance
    compatibility

.. toctree::
    :hidden:
    :caption: Elsewhere

    pyinfra on GitHub <http://github.com/Fizzadar/pyinfra>

..    pyinfra's website <http://pyinfra.com>
