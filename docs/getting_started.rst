Getting Started
===============

This guide should help describe the basics of deploying stuff with pyinfra. First install pyinfra using pip:

.. code:: bash

    pip install pyinfra

To do something with pyinfra you need two things:

**Inventory**:
    A set of hosts to target and any data/variables. Hosts can be in one or more groups and both groups and hosts can have different data associated with them.

**Operations**:
    Actions to take or state to apply to/on the hosts in the inventory. From simple shell commands to specific state such as "ensure this apt package is installed".


Ad-hoc commands with ``pyinfra``
--------------------------------

Let's start off executing a simple one off shell command. The first argument always specifies the inventory and the following arguments the operations to execute:

.. code:: shell

    # Usage:
    pyinfra INVENTORY OPERATIONS...

    # Execute an arbitrary shell command
    pyinfra my-server.net exec -- echo "hello world"

As you'll see, pyinfra runs the echo command and prints the output. See the :ref:`available command line options <cli:CLI arguments & options>` and :ref:`examples of ad-hoc commands <cli:Ad-hoc command execution>`.

More examples:

.. code:: shell

    # Ensure a package is installed on a Centos 8 instance
    pyinfra @vagrant/centos8 dnf.packages vim sudo=true

    # Ensure a package is installed on multiple instances
    pyinfra @vagrant/ubuntu18,@vagrant/debian9 apt.packages vim sudo=true


Create a Deploy
---------------

A deploy simply refers to a collection of inventories and operations defined in Python files. Unlike ad-hoc commands, pyinfra deploys can be saved and reused. Think of a deploy like Ansible's playbook or Chef's cookbook. We'll now replicate the above command line as a deploy.

To get started let's create an ``inventory.py`` containing our hosts to target:

.. code:: python

    # Define groups of hosts as lists
    my_hosts = ['my-server.net']

Now we need a ``deploy.py`` containing our operations to execute:

.. code:: python

    # Import pyinfra modules, each containing operations to use
    from pyinfra.modules import server

    # Ensure the state of a user
    server.shell(
        {'Execute hello world script'},  # name the operation
        'echo "hello world"',
    )

We can now execute this deploy like so:

.. code:: shell

    pyinfra -v inventory.py deploy.py  # the -v will print the command output (optional)

That's the basics of pyinfra! Possible next steps:

+ If you like to dive right into the code check out `the example deploys on GitHub <https://github.com/Fizzadar/pyinfra/tree/master/example>`_
+ You can also read the :doc:`building a deploy guide <./deploys>` which covers pyinfra's deploy features
+ Or :doc:`the CLI user guide <./cli>` which covers ad-hoc usage of pyinfra
+ Or look in the standalone_examples directory
