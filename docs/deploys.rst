Writing Deploys
===============

The definitive guide to writing ``pyinfra`` deploys.

What is a ``pyinfra`` deploy?
    A deploy represents a collection of inventory (hosts to target), data (configuration, templates, files) and operations (changes/state to apply to the inventory). Deploys are written in standard Python, and other packages can be used as needed.


Layout
------

The layout of a ``pyinfra`` deploy is generally very flexible. Only two paths are hard-coded, both relative to the Python file being executed:

+ ``group_data/*.py`` - arbitrary data for host groups
+ ``config.py`` - optional configuration

Although optional, it is recommended to use the following layout for other files:

+ ``*.py`` - top-level operation definitions
+ ``inventory.py`` or ``inventories/*.py`` - inventory definitions
+ ``templates/*.j2`` - `jinja2 <https://jinja.palletsprojects.com>`_ template files
+ ``files/*`` - normal/non-template files
+ ``tasks/*.py`` - operations to perform a specific task

An example layout:

.. code:: sh

    - setup_server.py  # deploy file containing operations to execute
    - update_server.py  # another deploy file with different operations
    - config.py  # optional pyinfra configuration
    inventories/
        - production.py  # production inventory targets
        - staging.py  # staging inventory targets
    group_data/
        - all.py  # global data variables
        - production.py  # production inventory only data variables
    tasks/
        - nginx.py  # deploy file containing task-specific operations
    files/
        - nginx.conf  # a file that can be uploaded with the `files.put` operation
    templates/
        - web.conf.j2  # a template that can be rendered & uploaded with the `files.template` operation


Inventory
---------

Inventory files contain groups of hosts. Groups are defined as a list or tuple of hosts. For example, this inventory creates two groups, "app_servers" and "db_servers":

.. code:: python

    # inventories/production.py

    app_servers = [
        'app-1.net',
        'app-2.net'
    ]

    db_servers = [
        'db-1.net',
        'db-2.net',
        'db-3.net'
    ]

**In addition to the groups defined in the inventory, all the hosts are added to two more groups: "all" and the name of the inventory file, in this case "production"**. Both can be overriden by defining them in the inventory.


.. _data-ref-label:

Data
----

Data allows you to separate deploy variables from the deploy script. With data per host and per group, you can easily build deploys that satisfy multiple environments. The :doc:`data example deploy <examples/data_multiple_environments>` shows this in action.

Host Data
~~~~~~~~~

Arbitrary data can be assigned in the inventory and used at deploy-time. You just pass a tuple ``(hostname, data)`` instead of just the hostname:

.. code:: python

    # inventories/production.py

    app_servers = [
        'app-1.net',
        ('app-2.net', {'some_key': True})
    ]

Group Data
~~~~~~~~~~

Group data files can be used to attach data to groups of host. They are placed in ``group_data/<group_name>.py``. This means ``group_data/all.py`` can be used to attach data to all hosts.

Data files are just Python, any core types will be included:

.. code:: python

    # group_data/production.py

    app_user = 'myuser'
    app_dir = '/opt/myapp'

Authenticating with Data
~~~~~~~~~~~~~~~~~~~~~~~~

Instead of passing ``--key``, ``--user``, etc to the CLI, or running a SSH agent, you can define these details within host and group data. The attributes available:

.. code:: python

    ssh_port = 22
    ssh_user = 'ubuntu'
    ssh_key = '~/.ssh/some_key'
    ssh_key_password = 'password for key'
    # ssh_password = 'Using password authorization is bad. Preferred option is ssh_key.'

Data Hierarchy
~~~~~~~~~~~~~~

The same keys can be defined for host and group data - this means we can set a default in *all.py* and override it on a group or host basis. When accessing data, the first match in the following is returned:

+ "Override" data passed in via CLI args
+ Host data as defined in the inventory file
+ Normal group data
+ "all" group data

.. Note::
    pyinfra contains a ``debug-inventory`` command which can be used to explore the data output per-host for a given inventory/deploy, ie ``pyinfra inventory.py debug-inventory``.


Operations
----------

Now that you've got an inventory of hosts and know how to authenticate with them, you can start writing operations. Operations are used to describe changes to make to the systems in the inventory. Operations are imported from ``pyinfra.operations``.

For example, this deploy will ensure that user "pyinfra" exists with home directory ``/home/pyinfra``, and that the ``/var/log/pyinfra.log`` file exists and is owned by that user.

.. code:: python

    # deploy.py

    # Import pyinfra modules, each containing operations to use
    from pyinfra.operations import server, files

    server.user(
        name='Create pyinfra user',
        user='pyinfra',
        home='/home/pyinfra',
    )

    files.file(
        name='Create pyinfra log file',
        path='/var/log/pyinfra.log',
        user='pyinfra',
        group='pyinfra',
        permissions='644',
        sudo=True,
    )

    # Execute with: pyinfra my-server.net deploy.py


Uses the :doc:`server module <./modules/server>` and :doc:`files module <./modules/files>`. You can see all available operations in :doc:`the operations index <./operations>`.

.. Important::
    Operations that rely on one another (interdependency) must be treated with caution. See: `deploy limitations <deploy_process.html#limitations>`_.

Global Arguments
~~~~~~~~~~~~~~~~

In addition to each operations having its own arguments, there are a number of keyword arguments available for all operations:

.. include:: _deploy_globals.rst

Using Data
~~~~~~~~~~

Adding data to inventories was :ref:`described above <data-ref-label>` - you can access it within a deploy on ``host.data``:

.. code:: python

    from pyinfra import host
    from pyinfra.operations import server

    # Ensure the state of a user based on host/group data
    server.user(
        name='Setup the app user',
        user=host.data.app_user,
        home=host.data.app_dir,
    )

Operation Meta
~~~~~~~~~~~~~~

Operation meta can be used during a deploy to change the desired operations:

.. code:: python

    from pyinfra.operations import server

    # Run an operation, collecting its meta output
    create_user = server.user(
        name='Create user myuser',
        user='myuser',
    }

    # If we added a user above, do something extra
    if create_user.changed:
        server.shell( # add user to sudo, etc...

Facts
~~~~~

Facts allow you to use information about the target host to change the operations you use. A good example is switching between `apt` & `yum` depending on the Linux distribution. Like data, facts are accessed using ``host.fact``:

.. code:: python

    from pyinfra import host
    from pyinfra.operations import yum

    if host.fact.linux_name == 'CentOS':
        yum.packages(
            name='Install nano via yum',
            packages=['nano'],
            sudo=True
        )

Some facts also take a single argument like the ``directory`` or ``file`` facts. The :doc:`facts index <./facts>` lists the available facts and their arguments.

Includes
~~~~~~~~

Including files can be used to break out operations into multiple files, often referred to as tasks. Files can be included using ``local.include``.

.. code:: python

    from pyinfra import local

    # Include & call all the operations in tasks/install_something.py
    local.include('tasks/install_something.py')

See more in :doc:`examples: groups & roles <./examples/groups_roles>`.


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
    When added to ``config.py`` (vs the deploy file), these options will take effect for any CLI usage (ie ``pyinfra host exec -- 'tail -f /var/log/syslog'``).
