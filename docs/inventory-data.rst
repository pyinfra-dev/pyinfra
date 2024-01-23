Inventory & Data
================

A pyinfra inventory provides hosts, groups and data. Host are the things pyinfra will make changes to (think a SSH daemon on a server, a Docker container or the local machine). Hosts can be attached to groups, and data can then be assigned to both the groups and individual hosts.

By default pyinfra assumes hosts are SSH servers and the name of the host is used as the SSH hostname. Prefixing the name of the host with ``@<connector-name>/`` is used to activate alternative connectors. See: :doc:`connectors`.

Inventory Files
---------------

Inventory files contain groups of hosts. Groups are defined as a ``list``. For example, this inventory creates two groups, ``app_servers`` and ``db_servers``:

.. code:: python

    app_servers = [
        "app-1.net",
        "app-2.net"
    ]

    db_servers = [
        "db-1.net",
        "db-2.net",
        "db-3.net",
    ]

If you save this file as ``inventory.py``, you can then use it in when executing pyinfra:

.. code:: shell

    pyinfra inventory.py OPERATIONS...

.. Note::
    In addition to the groups defined in the inventory, all the hosts are added to a group with the name of the inventory file (eg ``production.py`` becomes ``production``).

Limiting inventory at runtime
-----------------------------

It is possible to limit the inventory at execution time using the ``--limit`` argument. This makes pyinfra only execute operations against targets matching the limit. Multiple limits can be provided and a limit may refer to a group or glob-style match against host names. A few examples:

.. code:: shell

    # Only execute against @local
    pyinfra inventory.py deploy.py --limit @local

    # Only execute against hosts in the `app_servers` group
    pyinfra inventory.py deploy.py --limit app_servers

    # Only execute against hosts with names matching db*
    pyinfra inventory.py deploy.py --limit "db*"

    # Combine multiple limits
    pyinfra inventory.py deploy.py --limit app_servers --limit db-1.net

Host Data
---------

Data can be assigned to individual hosts in the inventory by using a tuple ``(hostname, data_dict)``:

.. code:: python

    app_servers = [
        ("app-1.net", {"install_postgres": False}),
        ("db-1.net", {"install_postgres": True}),
    ]

This can then be used in operations files:

.. code:: python

    from pyinfra import host

    if host.data.get("install_postgres"):
        apt.packages(
            packages=["postgresql-server"],
        )

Group Data Files
----------------

Group data can be stored in separate files under the ``group_data`` directory (there's also a ``--group-data $DIR`` flag). Files will be loaded that match ``group_data/<group_name>.py``, and all hosts in any matching group will receive variables defined in the file as data:

.. code:: python

    app_user = "myuser"
    app_dir = "/opt/pyinfra"

These can then be used in operations:

.. code:: python

    from pyinfra import host

    git.repo(
        src="git@github.com:Fizzadar/pyinfra.git",
        dest=host.data.app_dir,
        user=host.data.app_user,
    )

.. Note::
    The ``group_data`` directory is relative to the current working directory. This can be changed at runtime via the ``--chdir`` flag.

Data Hierarchy
--------------

The same keys can be defined for host and group data - this means we can set a default in ``all.py`` and override it on a group or host basis. When accessing data, the first match in the following is returned:

+ "Override" data passed in via CLI args
+ Host data as defined in the inventory file
+ Normal group data
+ "all" group data

.. Note::
    pyinfra contains a ``debug-inventory`` command which can be used to explore the data output per-host for a given inventory/deploy, ie ``pyinfra inventory.py debug-inventory``.

Connecting with Data
--------------------

Data can be used to configure connectors, for example setting SSH connection details can be done like so:

.. code:: python

    ssh_user = "ubuntu"
    ssh_key = "~/.ssh/some_key"
    ssh_key_password = "password for key"

The :doc:`connectors` contains full details of which data keys are available in each connector.

Global Arguments with Data
--------------------------

Data can also provide default values for :doc:`arguments`, for example:

.. code:: python

    _sudo = True
    _sudo_user = "pyinfra"

External Sources for Data
-------------------------

Because pyinfra is configured in Python, you can pull in data from pretty much anywhere just using other Python packages.
