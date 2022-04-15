Using Operations
================

Operations tell ``pyinfra`` what to do, for example the ``server.shell`` operation instructs ``pyinfra`` to execute a shell command. Most operations define state rather than actions - so instead of "start this service" you say "this service should be running" - ``pyinfra`` will only execute commands if needed.

For example, these operations will ensure that user ``pyinfra`` exists with home directory ``/home/pyinfra``, and that the ``/var/log/pyinfra.log`` file exists and is owned by that user:

.. code:: python

    # Import pyinfra modules, each containing operations to use
    from pyinfra.operations import server, files

    server.user(
        name="Create pyinfra user",
        user="pyinfra",
        home="/home/pyinfra",
    )

    files.file(
        name="Create pyinfra log file",
        path="/var/log/pyinfra.log",
        user="pyinfra",
        group="pyinfra",
        mode="644",
        _sudo=True,
    )


Uses :doc:`operations/files` and :doc:`operations/server`. You can see all available operations in the :doc:`operations`. If you save the file as ``deploy.py`` you can test it out using Docker:

.. code:: shell

    pyinfra @docker/ubuntu:20.04 deploy.py

.. Important::
    Operations that rely on one another (interdependency) must be treated with caution. See: `deploy limitations <deploy-process.html#limitations>`_.

Global Arguments
----------------

Global arguments are covered in detail here: :doc:`arguments`. There is a set of arguments available to all operations to control authentication (``_sudo``, etc) and operation execution (``_shell_executable``, etc):

.. code:: python

    from pyinfra.operations import apt

    apt.update(
        name="Update apt repositories",
        _sudo=True,
        _sudo_user="pyinfra",
    )

The ``host`` Object
-------------------

``pyinfra`` provides a global ``host`` object that can be used to retrieve information and metadata about the current host target. At all times the ``host`` variable represents the current host context, so you can think about the deploy code executing on individual hosts at a time.

The ``host`` object has ``name`` and ``groups`` attributes which can be used to control operation flow:

.. code:: python

    from pyinfra import host

    if host.name == "control-plane-1":
        ...

    if "control-plane" in host.groups:
        ...


Host Facts
~~~~~~~~~~

Facts allow you to use information about the target host to control and configure operations. A good example is switching between ``apt`` & ``yum`` depending on the Linux distribution. Facts are imported from ``pyinfra.facts.*`` and can be collected using ``host.get_fact(...)``:

.. code:: python

    from pyinfra import host
    from pyinfra.facts.server import LinuxName
    from pyinfra.operations import yum

    if host.get_fact(LinuxName) == "CentOS":
        yum.packages(
            name="Install nano via yum",
            packages=["nano"],
            _sudo=True
        )

See :doc:`facts` for a full list of available facts and arguments.

Host & Group Data
~~~~~~~~~~~~~~~~~

Adding data to inventories is covered in detail here: :doc:`inventory-data`. Data can be accessed within operations via the ``host.data`` attribute:

.. code:: python

    from pyinfra import host
    from pyinfra.operations import server

    # Ensure the state of a user based on host/group data
    server.user(
        name="Setup the app user",
        user=host.data.app_user,
        home=host.data.app_dir,
    )


The ``inventory`` Object
------------------------

Like ``host``, there is an ``inventory`` object that can be used to access the entire inventory of hosts. This is useful when you need facts or data from another host like the IP address of another node:

.. code:: python

    from pyinfra import inventory
    from pyinfra.facts.server import Hostname
    from pyinfra.operations import files

    # Get the other host, load the hostname fact
    db_host = inventory.get_host("postgres-main")
    db_hostname = db_host.get_fact(Hostname)

    files.template(
        name="Generate app config",
        src="templates/app-config.j2.yaml",
        dest="/opt/myapp/config.yaml",
        db_hostname=db_hostname,
    )

Operation Results
-----------------

All operations return an operation meta object which provides information about the changes the operation will execute. This can be used for subsequent operations:

.. code:: python

    from pyinfra.operations import server

    # Run an operation, collecting its meta output
    create_user = server.user(
        name="Create user myuser",
        user="myuser",
    }

    # If we added a user above, do something extra
    if create_user.changed:
        server.shell( # add user to sudo, etc...

Multiple Operation Files
------------------------

Including files can be used to break out operations across multiple files. Files can be included using ``local.include``.

.. code:: python

    from pyinfra import local

    # Include & call all the operations in tasks/install_something.py
    local.include("tasks/install_something.py")

See more in :doc:`examples: groups & roles <./examples/groups_roles>`.

.. Important::
    It is also possible to group operations into Python functions - see :doc:`packaging deploys <./api/deploys>` for more information.

Config
------

There are a number of configuration options for how deploys are managed. These can be defined at the top of a deploy file, or in a ``config.py`` alongside the deploy file. See :doc:`the full list of options & defaults <./apidoc/pyinfra.api.config>`.

.. code:: python

    # config.py or top of deploy.py

    # SSH connect timeout
    CONNECT_TIMEOUT = 1

    # Fail the entire deploy after 10% of hosts fail
    FAIL_PERCENT = 10

.. note::
    When added to ``config.py`` (vs the deploy file), these options will take effect for any CLI usage (ie ``pyinfra host exec -- "tail -f /var/log/syslog"``).

Requirements
~~~~~~~~~~~~

The config can be used to check Python package requirements before ``pyinfra`` executes, helping to prevent unexpected errors. This can either be defined as a requirements text file path or simply a list of requirements:

.. code:: python

    REQUIRE_PACKAGES = "requirements.txt"  # path relative to the deploy
    REQUIRE_PACKAGES = [
        "pyinfra~=1.1",
        "pyinfra-docker~=1.0",
    ]

Examples
--------

A great way to learn more about writing ``pyinfra`` deploys is to see some in action. There's a number of resources for this:

- `the pyinfra examples folder on GitHub <https://github.com/Fizzadar/pyinfra/tree/master/examples>`_ - a general collection of all kinds of example deploy
- :doc:`the example deploys in this documentation <./examples>` - these highlight specific common patterns
