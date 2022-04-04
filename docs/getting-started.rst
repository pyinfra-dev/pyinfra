Getting Started
===============

This guide should help describe the basics of deploying stuff with ``pyinfra``.


Install ``pyinfra`` with `pipx <https://pipxproject.github.io/pipx/>`_ (recommended) or ``pip`` (see :doc:`full install instructions <./install>`):

.. code:: bash

    pipx install pyinfra

To do something with pyinfra you need two things:

:doc:`Inventory <./inventory-data>`:
    Hosts, groups and data. Hosts are targets for ``pyinfra`` to execute commands or state changes (server via SSH, container via Docker, etc). Hosts can be attached to groups, and data can then be assigned to both the groups of hosts and individual hosts.

    By default ``pyinfra`` assumes hosts can be reached over SSH. ``pyinfra`` can connect to other systems using :doc:`connectors <./connectors>`, for example: a Docker container or the local machine.

:doc:`Operations <./using-operations>`:
    Commands to execute or state to apply to the target hosts in the inventory. These can be simple shell commands "execute the ``uptime`` command" or state definitions such as "ensure the ``iftop`` apt package is installed".

    Stateful operations will not generate changes unless required by diff-ing the target state against the state defined by operation arguments.

Ad-hoc commands with ``pyinfra``
--------------------------------

You can start ``pyinfra`` immediately with some ad-hoc command execution. The CLI always takes arguments in order ``INVENTORY`` then ``OPERATIONS``. You can target a SSH server, Docker container or the local machine for quick testing:

.. code:: shell

    pyinfra INVENTORY OPERATIONS...

    # Execute over SSH
    pyinfra my-server.net exec -- echo "hello world"

    # Execute within a new docker container
    pyinfra @docker/ubuntu:18.04 exec -- echo "hello world"

    # Execute on the local machine (MacOS/Linux only - for now)
    pyinfra @local exec -- echo "hello world"

When you run this ``pyinfra`` connects (or spins up a container), runs the echo command and prints the output. The :doc:`CLI page <./cli>` contains more :ref:`examples of ad-hoc commands <cli:Ad-hoc command execution>`.

State definitions
~~~~~~~~~~~~~~~~~

Operations can be used to define the desired state of target hosts. Where possible, ``pyinfra`` will then use the state to determine what, if any, changes need to be made to have targets reach that state. This means that when you run these commands for a second time, ``pyinfra`` won't need to do execute anything because the target is already up to date.

.. code:: shell

    # Ensure a package is installed on a Centos 8 instance
    pyinfra my-server.net dnf.packages vim

    # Stop a service on a remote host over SSH
    pyinfra my-server.net init.systemd httpd running=False _sudo=True

In this case you can re-run the above commands and in the second instance ``pyinfra`` will report no changes need to be made.

.. admonition:: Note for Docker users
    :class: note

    When using ``@docker/IMAGE`` syntax, ``pyinfra`` will use a new container each run (meaning there will always be changes). You can use the container from the first run in the second (``@docker/CTID``) to test the state cahnge handling.

Create a Deploy
---------------

A deploy is a collection of inventories and operations defined in Python files. These deploys can be saved and reused (committed to git, etc). Think of a deploy like Ansible's playbook or Chef's cookbook.

To get started create an ``inventory.py`` containing our hosts to target:

.. code:: python

    my_hosts = ["my-server.net", "@docker/ubuntu:18.04"]  # define a group as a list of hosts

Now create a ``deploy.py`` containing our operations to execute:

.. code:: python

    from pyinfra.operations import apt, server

    # Define some state - this operation will do nothing on subsequent runs
    apt.packages(
        name="Ensure the vim apt package is installed",
        packages=["vim"],
        _sudo=True,  # use sudo when installing the packages
    )

This can now be executed like this:

.. code:: shell

    pyinfra inventory.py deploy.py

That's the basics of ``pyinfra``!

Some good next steps:

+ :doc:`using-operations`
+ :doc:`inventory-data`
+ :doc:`arguments`
+ :doc:`cli`
+ :doc:`examples`
