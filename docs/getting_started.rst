Getting Started
===============

This guide should help describe the basics of deploying stuff with pyinfra.


Install & Usage
---------------

pyinfra requires `Python <https://python.org>`_ and can be installed with `pip <https://pip.pypa.io/en/stable/>`_:

.. code:: bash

    pip install pyinfra

    # pyinfra is used like so:
    pyinfra INVENTORY COMMANDS...


Executing Commands
------------------

To deploy something with pyinfra, you need an **inventory**. This specifies the target hosts, groups and any data associated with them. The simplest inventory is simply a comma separated list of target hostnames passed to the CLI. Let's start using pyinfra with a basic echo command:

.. code:: shell

    # On Unix systems:
    pyinfra @local exec -- echo "hello world"

    # On Windows you'll need a server to SSH into:
    pyinfra my-server.net exec -- echo "hello world"

As you'll see, pyinfra runs the echo command and prints the output.

``@local``:
    On *nix systems this special hostname can be used to execute commands on the local machine, without the need for SSH.


Create a Deploy
---------------

To write persistent (on disk) deploys with pyinfra you just use Python files. These, along with any associated files/templates/etc are called **deploys**. In this file you import the pyinfra modules needed and define the remote state desired with function calls. For example if you create a file ``deploy.py``:

.. code:: python

    # Import pyinfra modules, each containing operations to use
    from pyinfra.modules import files

    # Ensure the state of a user
    files.directory(
        'my_directory',
        sudo=True,
    )

Like above, this deploy ensures that the directory ``my_directory`` exists in the current/home directory. To execute the deploy:

.. code:: shell

    pyinfra my-server.net deploy.py

That's the basics of pyinfra! There's a lot of other features like facts, groups, data which are described in the :doc:`building a deploy guide <./deploys>`. Also see :doc:`the operations index <operations>` and `the example deploy on GitHub <http://github.com/Fizzadar/pyinfra/tree/develop/example>`_.
