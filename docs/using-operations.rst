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
    Operations that rely on one another (interdependency) must be treated with caution. See: `deploy limitations <deploy_process.html#limitations>`_.

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

Data
----

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

Facts
-----

Facts allow you to use information about the target host to control and configure operations. A good example is switching between ``apt`` & ``yum`` depending on the Linux distribution. Facts are imported from ``pyinfra.facts.*``:

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
