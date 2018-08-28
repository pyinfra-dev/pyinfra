pyinfra Documentation
=====================

pyinfra manages the state of one or more servers. It can be used for app/service deployment, config management and ad-hoc command execution. Deploys are asynchronous, highly performant and can target thousands of hosts in parallel. The inventory of servers and deploy state are written in Python, allowing for near-infinite extendability.

pyinfra targets POSIX compatibility and is currently tested against Ubuntu, Debian, CentOS,
Fedora & OpenBSD.

.. compound::
    :doc:`getting_started`
        A quickstart guide introducing the basics of pyinfra. Start here!

.. compound::
    :doc:`deploys`
        The definitive guide to building a deploy with pyinfra.

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
    operations
    facts
    patterns
    using_python

.. toctree::
    :hidden:
    :maxdepth: 1
    :caption: How pyinfra Works

    deploy_process
    performance
    compatibility

.. toctree::
    :hidden:
    :maxdepth: 1
    :caption: API Documentation

    api/example
    api/reference
    api/modules
    api/deploys

.. toctree::
    :hidden:
    :caption: Elsewhere

    pyinfra on GitHub <http://github.com/Fizzadar/pyinfra>

..    pyinfra's website <http://pyinfra.com>
