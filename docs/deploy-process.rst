How pyinfra Works
=================

pyinfra executes in five of stages:

1. **Setup** phase, read the inventory / data
2. **Connect** to the targets in the inventory
3. **Prepare** by detecting changes and determining operation order
4. **Execute** the changes on the targets
5. **Disconnect** and cleanup

Every time you run pyinfra it steps through each of these stages with the goal of updating the inventory to match the commands or state provided. Most of these stages are simple to reason about. The one exception to this is the **prepare**, or change detection, phase which is used to define the order operations are executed.

How pyinfra Detects Changes & Orders Operations
---------------------------------------------------

Below we'll look at an in depth example that explains why the prepare / ordering stage is so critical. This example deploys a single database server and three webservers, here's the inventory:

.. code:: python

    web_servers = ["web-01", "web-02", "web-03"]
    db_server = ["db-01"]

And here's the deploy code:

.. code:: python

    from pyinfra import host
    from pyinfra.operations import apt

    apt.packages(
        name="Install base debugging packages",
        packages=["htop", "iftop"],
        update=True,
        cache_time=3600,
    )

    if "db_server" in host.groups:
        apt.packages(
            name="Install postgres server",
            packages=["postgresql-server"],
        )

    if "web_servers" in host.groups:
        apt.packages(
            name="Install nginx",
            packages=["nginx"],
        )

The deploy code is written as if executing a single host. To execute it over multiple hosts requires pyinfra to run the code once for each host. We can't do this host by host or pyinfra would be really slow. But if we do it in parallel we can't ensure operations run in expected order.

The aim is that each operation runs in order, stopping at the end of operation until all hosts have completed or failed it before moving onto the next. So operations are sequential but each individual operation is executed on all hosts in parallel, like so:

.. code::

    - run "Install base debugging packages" on all hosts in parallel (web-01, web-02, web-03, db-01)
    - run "Install postgres server" on db-01
    - run "Upload postgres pg_hba config" on db-01
    - run "Install nginx" on web hosts in parallel (web-01, web-02, web-03)
    - run "Upload nginx config" on web hosts in parallel (web-01, web-02, web-03)

To make this possible we have to first execute the code to generate the order and then execute the actual operations. This is why deploy code is always executed before any changes are made.

When does this matter?
----------------------

Using Host Facts
~~~~~~~~~~~~~~~~

.. Caution::
    Only use immutable facts in deploy code (installed OS, Arch, etc) unless you are absolutely sure they will not change.

Let's look at an example - the deploy code here is bad but highlights the ordering problems:

.. code:: python

    from pyinfra import facts, host
    from pyinfra.operations import apt
    from pyinfra.facts.files import File

    apt.packages(
        name="Install nginx",
        packages=["nginx"],
    )

    if host.get_fact(File, path="/etc/nginx/sites-enabled/default"):
        files.file(
            name="Remove nginx default site",
            path="/etc/nginx/sites-enabled/default",
            present=False,
        )

The critical thing to remember is that when you execute ``pyinfra INVENTORY deploy.py`` the deploy code is run *before* the operations are actually executed. This enables pyinfra to figure out the correct order for operations (see below for a detailed explanation).

The problem here is the conditional check:

.. code:: python

    if host.get_fact(facts.files.File, path="/etc/nginx/sites-enabled/default"):

This gets executed *before* the ``apt.packages`` install, and evaluates to ``False``. But at execution time this would actually become ``True``. The solution is simple - rely on pyinfra's operations to describe the desired state and always call the second:

.. code:: python

    from pyinfra import facts, host
    from pyinfra.operations import apt, files

    apt.packages(
        name="Install nginx",
        packages=["nginx"],
    )

    files.file(
        name="Remove nginx default site",
        path="/etc/nginx/sites-enabled/default",
        present=False,
    )

In this case when the ``files.file`` operation is executed pyinfra will check if the file is present and remove it if so, and do nothing if not.

Checking Operation Changes
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. Caution::
    Always use the ``_if`` global argument when checking for previous operation changes.

Let's use a simple example as above with add a conditional reload based on the outcome of the ``files.file`` operation:

.. code:: python

    from pyinfra import facts, host
    from pyinfra.operations import apt, files, server

    apt.packages(
        name="Install nginx",
        packages=["nginx"],
    )

    remove_default_site = files.file(
        name="Remove nginx default site",
        path="/etc/nginx/sites-enabled/default",
        present=False,
    )

    if remove_default_site.changed:
        server.service(
            name="Reload nginx",
            service="nginx",
            reloaded=True,
        )

As above, the problem here is again the conditional check:

.. code:: python

    if remove_default_site.changed:

Since this gets executed before nginx is installed by ``apt.packages`` operation, the value of ``remove_default_site.changed`` at this stage is ``False`` but at execution time this would become ``True``, exactly like the fact example above. The solution here is to use the ``_if`` global argument to delay the check until execution time:

.. code:: python

    from pyinfra import facts, host
    from pyinfra.operations import apt, files, server

    apt.packages(
        name="Install nginx",
        packages=["nginx"],
    )

    remove_default_site = files.file(
        name="Remove nginx default site",
        path="/etc/nginx/sites-enabled/default",
        present=False,
    )

    server.service(
        name="Reload nginx",
        service="nginx",
        reloaded=True,
        _if=remove_default_site.did_change,
    )
