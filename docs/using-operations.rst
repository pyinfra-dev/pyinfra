Using Operations
================

.. admonition:: What are operations?
    :class: tip

    Operations tell pyinfra what to do, for example the ``server.shell`` operation instructs pyinfra to execute a shell command. Most operations define state rather than actions - so instead of *start this service* you say *this service should be running* - pyinfra will make changes if needed.

For example, these two operations will ensure that user ``pyinfra`` exists with home directory ``/home/pyinfra``, and that the ``/var/log/pyinfra.log`` file exists and is owned by that user:

.. code:: python

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

pyinfra provides a global ``host`` object that can be used to retrieve information and metadata about the current host target. At all times the ``host`` variable represents the current host context, so you can think about the deploy code executing on individual hosts at a time.

The ``host`` object has ``name`` and ``groups`` attributes which can be used to control operation flow:

.. code:: python

    from pyinfra import host

    if host.name == "control-plane-1":
        ...

    if "control-plane" in host.groups:
        ...

Host & Group Data
~~~~~~~~~~~~~~~~~

Adding data to inventories is covered in detail here: :doc:`inventory-data`. Data can be accessed within operations using the ``host.data`` attribute:

.. code:: python

    from pyinfra import host
    from pyinfra.operations import server

    # Ensure the state of a user based on host/group data
    server.user(
        name="Setup the app user",
        user=host.data.app_user,
        home=host.data.app_dir,
    )


Host Facts
~~~~~~~~~~

Facts allow you to use information about the target host to control and configure operations. A good example is switching between ``apt`` & ``yum`` depending on the Linux distribution. Facts are imported from ``pyinfra.facts.*`` and can be retrieved using the ``host.get_fact`` function:

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

.. Important::
    Only use immutable facts in deploy code (installed OS, Arch, etc) unless you are absolutely sure they will not change. See: `using host facts <deploy-process.html#using-host-facts>`_.

Fact Errors
~~~~~~~~~~~

When facts fail due to an error the host will be marked as failed just as it would when an operation fails. This can be avoided by passing the ``_ignore_errors`` argument:

.. code:: python

    if host.get_fact(LinuxName, _ignore_errors=True):
        ...

The ``inventory`` Object
------------------------

Like ``host``, there is an ``inventory`` object that can be used to access the entire inventory of hosts. This is useful when you need facts or data from another host like the hostname of another server:

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


Operation Changes & Output
--------------------------

All operations return an operation meta object which provides information about the changes the operation *will* execute. This can be used to control other operations via the ``_if`` argument:

.. code:: python

    from pyinfra.operations import server

    create_user = server.user(
        name="Create user myuser",
        user="myuser",
    )

    create_otheruser = server.user(
        name="Create user otheruser",
        user="otheruser",
    )

    server.shell(
        name="Bootstrap myuser",
        commands=["..."],
        _if=create_user.did_change,
    )

    # A list can be provided to run an operation if **all** functions return true
    server.shell(
        commands=["echo 'Both myuser and otheruser changed'"],
        _if=[create_user.did_change, create_otheruser.did_change],
    )

    # You can also build your own lamba functions to achieve, e.g. an OR condition
    server.shell(
        commands=["echo 'myuser or otheruser changed'"],
        _if=lambda: create_user.did_change() or create_otheruser.did_change(),
    )

    # The functions `any_changed` and `all_changed` are provided for common use cases, e.g.
    from pyinfra.operations.util import any_changed, all_changed
    server.shell(commands=["..."], _if=any_changed(create_user, create_otheruser))
    server.shell(commands=["..."], _if=all_changed(create_user, create_otheruser))

Operation Output
~~~~~~~~~~~~~~~~

pyinfra doesn't immediately execute operations, meaning output is not available right away. It is possible to access this output at runtime by providing a callback function using the :ref:`operations:python.call` operation.

.. code:: python

    from pyinfra import logger
    from pyinfra.operations import python, server

    result = server.shell(
        commands=["echo output"],
    )
    # result.stdout raises exception here, but works inside callback()

    def callback():
        logger.info(f"Got result: {result.stdout}")

    python.call(
        name="Execute callback function",
        function=callback,
    )


Nested Operations
-----------------

Nested operations are called during the execution phase within a callback function passed into a :ref:`operations:python.call`. Calling a nested operation immediately executes it on the target machine. This is useful in complex scenarios where one operation output is required in another.

Because nested operations are executed immediately, the output is always available right away:

.. code:: python

    from pyinfra import logger
    from pyinfra.operations import python, server

    def callback():
        result = server.shell(
            commands=["echo output"],
        )

        logger.info(f"Got result: {result.stdout}")

    python.call(
        name="Execute callback function",
        function=callback,
    )


Include Multiple Files
----------------------

Including files can be used to break out operations across multiple files. Files can be included using ``local.include``.

.. code:: python

    from pyinfra import local

    # Include & call all the operations in tasks/install_something.py
    local.include("tasks/install_something.py")

Additional data can be passed across files via the ``data`` param to parameterize tasks and is available in ``host.data``. For example `tasks/create_user.py` could look like:

.. code:: python

    from getpass import getpass

    from pyinfra import host
    from pyinfra.operations import server

    group = host.data.get("group")
    user = host.data.get("user")

    server.group(
        name=f"Ensure {group} is present",
        group=group,
    )
    server.user(
        name=f"Ensure {user} is present",
        user=user,
        group=group,
    )

And and be called by other deploy scripts or tasks:

.. code:: python

    from pyinfra import local

    for group, user in (("admin", "Bob"), ("admin", "Joe")):
        local.include("tasks/create_user.py", data={"group": group, "user": user})

See more in :doc:`examples: groups & roles <./examples/groups_roles>`.


The ``config`` Object
---------------------

Like ``host`` and ``inventory``, ``config`` can be used to set global defaults for operations. For example, to use sudo in all following operations:

.. code:: python

    from pyinfra import config

    config.SUDO = True

    # all operations below will use sudo by default (unless overridden by `_sudo=False`)

Enforcing Requirements
~~~~~~~~~~~~~~~~~~~~~~

The config object can be used to enforce a pyinfra version or Python package requirements. This can either be defined as a requirements text file path or simply a list of requirements:

.. code:: python

    # Require a certain pyinfra version
    config.REQUIRE_PYINFRA_VERSION = "~=1.1"

    # Require certain packages
    config.REQUIRE_PACKAGES = "requirements.txt"  # path relative to the current working directory
    config.REQUIRE_PACKAGES = [
        "pyinfra~=1.1",
        "pyinfra-docker~=1.0",
    ]


Examples
--------

A great way to learn more about writing pyinfra deploys is to see some in action. There's a number of resources for this:

- `the pyinfra examples folder on GitHub <https://github.com/Fizzadar/pyinfra/tree/2.x/examples>`_ - a general collection of all kinds of example deploy
- :doc:`the example deploys in this documentation <./examples>` - these highlight specific common patterns
