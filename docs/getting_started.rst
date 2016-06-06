Getting Started
===============

This guide should help describe the basics of deploying stuff with pyinfra.


Install
-------

pyinfra requires `Python <https://python.org>`_ and can be installed with ``pip``:

.. code:: bash

    $ pip install pyinfra
    ...
    $ pyinfra (on Windows: python -m pyinfra)

    Usage:
        pyinfra -i INVENTORY DEPLOY [-v -vv options]
        pyinfra -i INVENTORY --run OP ARGS [-v -vv options]
        pyinfra -i INVENTORY --fact FACT [-v options]
        pyinfra -i INVENTORY [DEPLOY] --debug-data [options]
        pyinfra (--facts | --help | --version)


Command Line Ops
----------------

To deploy something with pyinfra, you need an **inventory** and some **operations**:

+ **The inventory** holds the target hosts, groups and any data associated with them
+ **The operations** define the desired state of the target hosts, and are grouped as **modules**

Lets start by running a deploy that will ensure user "fred" exists, using the ``server.user`` operation:

.. code:: shell

    pyinfra -i my-server.host --run server.user fred --sudo  # --user, --key

The ``--sudo`` flag used to run the operation with sudo. To connect & authenticate with the remote host you can use the ``--port``, ``--user``, ``--key`` and password ``--password`` flags.


The Deploy File
---------------

To write persistent (on disk) deploys with pyinfra you just use a Python file, eg. *deploy.py*. In this file you import the pyinfra modules needed and define the remote state desired with function calls:

.. code:: python

    # Import pyinfra modules, each containing operations to use
    from pyinfra.modules import server

    # Ensure the state of a user
    server.user(
        'vivian',
        sudo=True
    )

Like above, this deploy ensures user "vivian" exists, using the :doc:`server module <./modules/server>`. To execute the deploy:

.. code:: shell

    pyinfra -i my-server.host deploy.py

That's the basics of pyinfra! There's a lot of other features like facts, groups, data which are described in the :doc:`building a deploy guide <./building_a_deploy>`. Also see :doc:`the modules index <modules>` and `the example deploy on GitHub <http://github.com/Fizzadar/pyinfra/tree/develop/example>`_.
