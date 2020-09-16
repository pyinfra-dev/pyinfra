Getting Started
===============

This guide should help describe the basics of deploying stuff with ``pyinfra``.


Install ``pyinfra`` with pip or `pipx <https://pipxproject.github.io/pipx/>`_ (see :doc:`full install instructions <./install>`):

.. code:: bash

    pip install pyinfra

To do something with pyinfra you need two things:

**Inventory**:
    Hosts, groups and data. Hosts are targets for ``pyinfra`` to execute commands or state changes. Hosts can belong to one or more groups, and both groups and hosts can have data associated with them.

    By default ``pyinfra`` assumes hosts can be reached over SSH. ``pyinfra`` can connect to other systems using :doc:`connectors <./connectors>`, for example: a Docker container or the local machine.

**Operations**:
    Commands to execute or state to apply to the target hosts in the inventory. These can be simple shell commands "execute the ``uptime`` command" or state definitions such as "ensure the ``iftop`` apt package is installed".


Ad-hoc commands with ``pyinfra``
--------------------------------

Let's start off executing a simple ad-hoc shell command. The **first argument always specifies the inventory** and the **following arguments specify the operations**:

.. code:: shell

    pyinfra INVENTORY OPERATIONS...

    # Execute an arbitrary shell command over SSH
    pyinfra my-server.net exec -- echo "hello world"

    # Execute a shell command within a docker container
    pyinfra @docker/ubuntu:18.04 exec -- bash --version

As you'll see, ``pyinfra`` runs the echo command and prints the output. The :doc:`CLI page <./cli>` contains more :ref:`examples of ad-hoc commands <cli:Ad-hoc command execution>`.

State definitions
~~~~~~~~~~~~~~~~~

Now that we can execute ad-hoc shell commands, let's define some state to ensure. The key feature here is that when you run these commands for a second time, ``pyinfra`` won't need to do execute anything because the target is already up to date. You can read more about how this works in :doc:`./deploy_process`.

.. code:: shell

    # Ensure a package is installed on a Centos 8 instance
    pyinfra @docker/centos:8 dnf.packages vim sudo=true

    # Ensure a package is installed on multiple instances
    pyinfra @docker/ubuntu:18.04,@docker/debian:9 apt.packages vim sudo=true

    # Stop a service on a remote host over SSH
    pyinfra my-server.net init.systemd httpd sudo=True running=False

In this case you can re-run the above commands and in the second instance ``pyinfra`` will report no changes need to be made.


Create a Deploy
---------------

A deploy is a collection of inventories and operations defined in Python files. These deploys can be saved and reused (committed to git, etc). Think of a deploy like Ansible's playbook or Chef's cookbook. We'll now replicate the above hello world ad-hoc command as a deploy.

To get started let's create an ``inventory.py`` containing our hosts to target:

.. code:: python

    my_hosts = ['my-server.net', '@docker/ubuntu:18.04']  # define a group as a list of hosts

Now we need a ``deploy.py`` containing our operations to execute:

.. code:: python

    from pyinfra.operations import apt, server

    server.shell(
        name='Run an ad-hoc command',  # optional name for the operation
        commands='echo "hello world"',
    )

    # Define some state - this operation will do nothing on subsequent runs
    apt.packages(
        name='Ensure the vim apt package is installed',
        packages=['vim'],
        sudo=True,  # use sudo when installing the packages
    )

We can now execute this deploy like so:

.. code:: shell

    pyinfra inventory.py deploy.py

That's the basics of ``pyinfra``! Possible next steps:

+ If you like to dive right into the code check out `the examples on GitHub <https://github.com/Fizzadar/pyinfra/tree/master/examples>`_.
+ Read the :doc:`building a deploy guide <./deploys>` which covers pyinfra's deploy features.
+ Or :doc:`the CLI user guide <./cli>` which covers ad-hoc usage of ``pyinfra``.
