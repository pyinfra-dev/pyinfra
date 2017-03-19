pyinfra
=======

pyinfra manages the state of one or more servers. It can be used for app/service deployment, config management and ad-hoc command execution. Deploys are asynchronous, highly performant and can target thousands of hosts in parallel. The inventory of servers and deploy state are written in Python, allowing for near-infinite extendability.

pyinfra targets POSIX compatability and is currently tested against Ubuntu, Debian, CentOS,
Fedora & OpenBSD.

.. toctree::
    :maxdepth: 1
    :caption: Using pyinfra

    getting_started
    building_a_deploy
    modules
    facts
    patterns

.. toctree::
    :maxdepth: 1
    :caption: How pyinfra Works

    deploy_process
    performance
    compatability

.. toctree::
    :maxdepth: 1
    :caption: API Documentation

    api/example
    api/reference
    api/operations
    api/facts


Meta
----

+ :ref:`genindex`
+ :ref:`modindex`

.. toctree::
    :hidden:
    :caption: Elsewhere

    pyinfra on GitHub <http://github.com/Fizzadar/pyinfra>

..    pyinfra's website <http://pyinfra.com>
