Writing Deploys
===============

The definitive guide to writing a pyinfra deploys.

What's a deploy?
    A deploy represents a collection of inventory (hosts to target), data (configuration, templates, files) and operations (changes/state to apply to the inventory). Deploys are written in standard Python, and other packages can be used as needed.


Layout
------

+ ``*.py`` - top-level operations
+ ``inventories/*.py`` - groups of hosts and individual host data
+ ``group_data/*.py`` - arbitrary data for host groups
+ ``templates/*.jn2`` - templates files
+ ``files/*`` - normal/non-template files
+ ``tasks/*.py`` - operations to perform a specific task
+ ``config.py`` - optional config and hooks


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
    # ssh_password = 'password auth is bad'

Data Hierarchy
~~~~~~~~~~~~~~

The same keys can be defined for host and group data - this means we can set a default in *all.py* and override it on a group or host basis. When accessing data, the first match in the following is returned:

+ "Override" data passed in via CLI args
+ Host data as defined in the inventory file
+ Normal group data
+ "all" group data

.. note::
    pyinfra contains a ``debug-inventory`` command which can be used to explore the data output per-host for a given inventory/deploy, ie ``pyinfra inventory.py debug-inventory``.


Operations
----------

Now that you've got an inventory of hosts and know how to auth with them, you can start writing operations. Operations are used to describe changes to make to the systems in the inventory. Operations are namespaced and imported from ``pyinfra.modules``.

For example, this deploy will ensure that user "pyinfra" exists with home directory ``/home/pyinfra``, and that the ``/var/log/pyinfra.log`` file exists and is owned by that user.

.. code:: python

    # deploy.py

    # Import pyinfra modules, each containing operations to use
    from pyinfra.modules import server, files

    # Ensure the state of a user
    server.user(
        {'Create pyinfra user'},
        'pyinfra',
        home='/home/pyinfra',
    )

    # Ensure the state of files
    files.file(
        {'Create pyinfra log file'},
        '/var/log/pyinfra.log',
        user='pyinfra',
        group='pyinfra',
        permissions='644',
        sudo=True,
    )

    # Execute with: pyinfra my-server.net deploy.py


Uses the :doc:`server module <./modules/server>` and :doc:`files module <./modules/files>`. You can see all the modules in :doc:`the modules index <./operations>`.

.. note::
    Pass a ``set`` object as the first argument to name the operation (as above), which will appear during a deploy. By default the operation module, name and arguments are shown.

Global Arguments
~~~~~~~~~~~~~~~~

In addition to each operations own arguments, there are a number of keyword arguments available in all operations:

.. include:: _deploy_globals.rst

Using Data
~~~~~~~~~~

Adding data to inventories was :ref:`described above <data-ref-label>` - you can access it within a deploy on ``host.data``:

.. code:: python

    from pyinfra import host
    from pyinfra.modules import server

    # Ensure the state of a user based on host/group data
    server.user(
        {'Setup the app user'},
        host.data.app_user,
        home=host.data.app_dir,
    )

Operation Meta
~~~~~~~~~~~~~~

Operation meta can be used during a deploy to change the desired operations:

.. code:: python

    from pyinfra.modules import server

    # Run an operation, collecting its meta output
    create_user = server.user(
        {'Create user myuser'},
        'myuser',
    }

    # If we added a user above, do something extra
    if create_user.changed:
        server.shell('# add user to sudo, etc...')

Facts
~~~~~

Facts allow you to use information about the target host to change the operations you use. A good example is switching between apt & yum depending on the Linux distribution. Like data, facts are accessed on ``host.fact``:

.. code:: python

    from pyinfra import host
    from pyinfra.modules import yum

    if host.fact.linux_name == 'CentOS':
        yum.packages(
            'nano',
            sudo=True
        )

Some facts also take a single argument, for example the ``directory`` or ``file`` facts. The :doc:`facts index <./facts>` lists the available facts and their arguments.

Includes
~~~~~~~~

Including files can be used to break out operations into multiple files, often referred to as tasks. Files can be included using ``local.include``.

.. code:: python

    from pyinfra import local, inventory

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
    When added to ``config.py`` (vs the deploy file), these options will take affect for any CLI usage (ie ``pyinfra host exec -- 'tail -f /var/log/syslog'``).


Hooks
-----

Deploy hooks are executed by the CLI at various points during the deploy process. These can be defined in a ``config.py``:

+ ``before_connect``
+ ``before_facts``
+ ``before_deploy``
+ ``after_deploy``

These can be used, for example, to check the right branch before connecting or to build some clientside assets locally before fact gathering. Hooks all take ``data, state`` as arguments:

.. code:: python

    # config.py

    from pyinfra import hook

    @hook.before_connect
    def my_callback(data, state):
        print('Before connect hook!')

To abort a deploy, a hook can raise a ``hook.Error`` which the CLI will handle.

When executing commands locally inside a hook (ie ``webpack build``), you should always use the ``pyinfra.local`` module:

.. code:: python

    @hook.before_connect
    def my_callback(data, state):
        # Check something local is correct, etc
        branch = local.shell('git rev-parse --abbrev-ref HEAD')
        app_branch = data.app_branch

        if branch != app_branch:
            # Raise hook.Error for pyinfra to handle
            raise hook.Error('We\'re on the wrong branch (want {0}, got {1})!'.format(
                branch, app_branch
            ))
