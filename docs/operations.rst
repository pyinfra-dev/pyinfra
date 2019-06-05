Operations Index
================

Operations are used to describe changes to make to systems in the inventory. You use them to define state and pyinfra will make any necessary changes to reach that state. They can be executed via the `command line <getting_started.html#using-the-pyinfra-command-line>`_ or by :doc:`creating a deploy <deploys>`.

All operations accept a set of `global arguments <deploys.html#global-arguments>`_ and are namespaced as different modules:

.. toctree::
   :maxdepth: 2
   :glob:

   modules/*
