.. meta::
    :description: Frequently asked pyinfra questions
    :keywords: pyinfra, documentation, faq


Frequently Asked Questions
==========================

How do I get the name of the current host?
------------------------------------------

The currently executing host can be fetched from the ``host`` context variable. If you need the hostname the ``server.Hostname`` fact can be used to get that:

.. code:: python

    # Get the name of the host as defined in the inventory
    from pyinfra import host
    name = host.name

    # Get the actual current hostname from the host
    from pyinfra.facts.server import Hostname
    hostname = host.get_fact(Hostname)

How do I use sudo in an operation?
----------------------------------

Sudo is controlled by one of the `privilege and user escalation arguments <arguments.html#privilege-user-escalation>`_, there are a number of additional arguments to control sudo execution:

.. code:: python

    apt.packages(
        packages=["iftop"],
        _sudo=True,
        _sudo_user="someuser",    # sudo to this user
        _use_sudo_login=True,     # use a login shell when sudo-ing
        _preserve_sudo_env=True,  # preserve the environment when sudo-ing
    )

How do I chmod or chown a file/directory/link?
----------------------------------------------

Use the LINK ``files.file``, ``files.directory`` or ``files.link`` operations to set the permissions and ownership of files, directories & links:

.. code:: python

    files.file(
        path="/etc/default/elasticsearch",
        user="pyinfra",
        group="pyinfra",
        mode=644,
    )
