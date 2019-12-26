Facts Index
===========

pyinfra uses facts to determine the existing state of a remote server. Operations use this information to generate commands which alter the state. Facts can be executed/tested via the command line:

.. code:: sh

    pyinfra myhost.com fact date another_fact ...

If you want to pass an argument to a fact, use `:` then the argument. For example:

    pyinfra myhost.com fact deb_package:openssh-server

Or as part of :doc:`a deploy <deploys>`:

.. code:: py

    if host.fact.linux_name == 'Ubuntu':
        apt.packages(...)

Facts, like :doc:`operations <operations>`, are namespaced as different modules - shortcuts to each of these can be found in the sidebar.

.. toctree::
   :maxdepth: 2
   :glob:

   facts/*
