.. meta::
    :description: Frequently asked pyinfra questions
    :keywords: pyinfra, documentation, faq


Frequently Asked Questions
==========================

How do I get the name of the current host?
------------------------------------------

The currently executing host can be fetched from a global context variable within operation code:

.. code:: python

    from pyinfra import host

    host.name  # the name of the host, as defined in the inventory

How do I use sudo in an operation?
----------------------------------

Sudo is controlled by one of the :doc:`arguments`, there are a number of additional arguments to control sudo execution:

.. code:: python

    apt.packages(
        packages=["iftop"],
        _sudo=True,
        _sudo_user="someuser",    # sudo to this user
        _use_sudo_login=True,     # use a login shell when sudo-ing
        _preserve_sudo_env=True,  # preserve the environment when sudo-ing
    )
