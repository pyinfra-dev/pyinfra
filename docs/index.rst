pyinfra
=======

pyinfra automates service deployment. It does this by diffing the state of the server with the state defined in the deploy script. Deploys are asyncronous and highly performant. The inventory & deploy are managed with pure Python, allowing for near-infinite extendability.

pyinfra targets POSIX compatability and is currently tested against Ubuntu, Debian, CentOS
& OpenBSD.

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
    operations
    performance

.. toctree::
    :maxdepth: 1
    :caption: API Documentation

    api_example
    api_reference

Meta
----

+ :ref:`genindex`
+ :ref:`modindex`

.. toctree::
    :hidden:
    :caption: Elsewhere

    pyinfra on GitHub <http://github.com/Fizzadar/pyinfra>

..    pyinfra's website <http://pyinfra.com>
