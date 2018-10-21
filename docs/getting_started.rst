Getting Started
===============

This guide should help describe the basics of deploying stuff with pyinfra. pyinfra can be installed with `pip <https://pip.pypa.io/en/stable/>`_:

.. code:: bash

    pip install pyinfra


Using the ``pyinfra`` command line
----------------------------------

To do something with pyinfra you need two things:

**Inventory**:
    A set of hosts to target and any associated data. This can be a simple list of hosts or multiple gorups of different hosts with different data for each group.

**Operations**:
    Things to execute or ensure on the hosts in the inventory. This can be anything from shell commands to ensuring a given apt package is installed. These can be passed to the CLI directly or written into Python files, ie ``deploy.py`` and persisted to disk (and source code management).

Let's start off executing a simple shell command. The first argument always specifies the inventory and the following arguments the operations to execute:

.. code:: shell

    # Usage:
    pyinfra INVENTORY OPERATIONS...

    # On Unix systems:
    pyinfra @local exec -- echo "hello world"

    # On Windows you'll need a server to SSH into:
    pyinfra my-server.net exec -- echo "hello world"

As you'll see, pyinfra runs the echo command and prints the output.

``@local``:
    On *nix systems this special hostname can be used to execute commands on the local machine, without the need for SSH.


Create a Deploy
---------------

To write persistent (on disk) deploys with pyinfra you just use Python files. These, along with any associated files/templates/etc are called **deploys**. For example, let's create an ``inventory.py``:

.. code:: python

    # Define groups of hosts as lists
    my_hosts = ['my-server.net']

And a ``deploy.py`` alongside:

.. code:: python

    # Import pyinfra modules, each containing operations to use
    from pyinfra.modules import server

    # Ensure the state of a user
    server.shell(
        {'Execute hello world script'},  # name the operation
        'echo "hello world"',
        sudo=True,
    )

And execute the deploy with:

.. code:: shell

    pyinfra inventory.py deploy.py

That's the basics of pyinfra! There's a lot of other features like facts, groups, data which are described in the :doc:`building a deploy guide <./deploys>`. Also see :doc:`the operations index <operations>` and `the example deploy on GitHub <http://github.com/Fizzadar/pyinfra/tree/develop/example>`_.
