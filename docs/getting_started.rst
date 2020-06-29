Getting Started
===============

This guide should help describe the basics of deploying stuff with ``pyinfra``.


Install ``pyinfra`` with pip or `pipx <https://pipxproject.github.io/pipx/>`_ (see :doc:`full install instructions <./install>`):

.. code:: bash

    pip install pyinfra

To do something with pyinfra you need two things:

**Inventory**:
    Hosts, groups and data. Hosts are targets for pyinfra to execute commands or state changes. Hosts can belong to one or more groups, and both groups and hosts can have data associated with them. Examples: an SSH server, a Docker container, the local machine.

**Operations**:
    Commands to execute or state to apply to the target hosts in the inventory. These can be simple shell commands (``uptime``) or state definitions such as "ensure the ``iftop`` apt package is installed".

Ad-hoc commands with ``pyinfra``
--------------------------------

Let's start off executing a simple ad-hoc shell command. The first argument always specifies the inventory and the following arguments the operations to execute:

.. code:: shell

    pyinfra INVENTORY OPERATIONS...

    # Execute an arbitrary shell command
    pyinfra my-server.net exec -- echo "hello world"

    # Execute a shell command within a docker container
    pyinfra @docker/ubuntu exec -- bash --version

As you'll see, ``pyinfra`` runs the echo command and prints the output. See the :ref:`available command line options <cli:CLI arguments & options>` and :ref:`examples of ad-hoc commands <cli:Ad-hoc command execution>`.

State definitions
~~~~~~~~~~~~~~~~~

Now that we can execute ad-hoc shell commands, let's define some state to ensure. The key feature here is that when you run these commands for a second time, ``pyinfra`` won't need to do execute anything because the target is already up to date. You can read more about how this works in :doc:`./deploy_process`.

.. code:: shell

    # Ensure a package is installed on a Centos 8 instance
    pyinfra @docker/centos8 dnf.packages vim sudo=true

    # Ensure a package is installed on multiple instances
    pyinfra @docker/ubuntu18,@docker/debian9 apt.packages vim sudo=true

    # Stop a service on a remote host
    pyinfra some_remote_host init.systemd httpd sudo=True running=False


Create a Deploy
---------------

A deploy is a collection of inventories and operations defined in Python files. These deploys can be saved and reused (committed to git, etc). Think of a deploy like Ansible's playbook or Chef's cookbook. We'll now replicate the above hello world ad-hoc command as a deploy.

To get started let's create an ``inventory.py`` containing our hosts to target:

.. code:: python

    # Define groups of hosts as lists
    my_hosts = ['my-server.net']

Now we need a ``deploy.py`` containing our operations to execute:

.. code:: python

    from pyinfra.operations import apt, server

    # Run an ad-hoc command
    server.shell(
        {'Execute hello world script'},  # Use a set as the first argument to name the operation
        'echo "hello world"',
    )

    # Define some state - this operation will do nothing on subsequent runs
    apt.packages(
        {'Install vim apt package'},
        'vim',
        sudo=True,  # use sudo when installing the packages
    )

We can now execute this deploy like so:

.. code:: shell

    pyinfra -v inventory.py deploy.py  # the optional verbose flag '-v' will print the command output

That's the basics of ``pyinfra``! Possible next steps:

+ If you like to dive right into the code check out `the examples on GitHub <https://github.com/Fizzadar/pyinfra/tree/master/examples>`_
+ You can also read the :doc:`building a deploy guide <./deploys>` which covers pyinfra's deploy features
+ Or :doc:`the CLI user guide <./cli>` which covers ad-hoc usage of ``pyinfra``.
