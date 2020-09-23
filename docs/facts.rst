Facts Index
===========

``pyinfra`` uses **facts** to determine the existing state of a remote server. Operations use this information to generate commands which alter the state. Facts are read-only and is populated at the beginning of the deploy.

Facts can be executed/tested via the command line:

.. code:: sh

    # Example how to get multiple facts from a server myhost.com
    pyinfra myhost.com fact date another_fact ...

If you want to see all facts:

.. code:: sh

    # Show all of the facts from myhost.com
    pyinfra myhost.com all-facts

If you want to pass an argument to a fact, use `:` then the argument. For example:

.. code:: sh

    # See if the package 'openssh-server' is installed servers myhost.com and myhost2.com
    pyinfra myhost.com,myhost2.com fact deb_package:openssh-server

You can leverage facts as part of :doc:`a deploy <deploys>` like this:

.. code:: py

    # If this is an Ubuntu server
    if host.fact.linux_name == 'Ubuntu':
        apt.packages(...)

**Want a new fact?** Check out :doc:`the writing facts guide <./api/facts>`.

Facts, like :doc:`operations <operations>`, are namespaced as different modules - shortcuts to each of these can be found in the sidebar.

.. toctree::
   :maxdepth: 2
   :glob:

   facts/*
