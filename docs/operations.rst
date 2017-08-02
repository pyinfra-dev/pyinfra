Operations Index
================

Operations are used to describe changes to make to systems in the inventory. You use them to define state and pyinfra will make any necessary changes to reach that state. They can be executed via the command line:

.. code:: sh

    pyinfra my-host.net files.directory /opt/my_app,user=ubuntu

Or by :doc:`creating a deploy <deploys>`:

.. code:: py

    files.directory(
        {'Create app directory'},
        '/opt/my_app',
        user='ubuntu',
    )

Operations are namespaced as different modules:

.. toctree::
   :maxdepth: 2
   :glob:

   modules/*
