Operations Index
================

Operations are used to describe changes to make to systems in the inventory. Use them to define state and ``pyinfra`` will make any necessary changes to reach that state. Operations can be executed via the `command line <getting_started.html#using-the-pyinfra-command-line>`_ or by :doc:`creating a deploy <deploys>`.

**Want a new operation?** Check out :doc:`the writing operations guide <./api/operations>`.

All operations accept a set of `global arguments <deploys.html#global-arguments>`_ and are grouped as Python modules.


.. toctree::
   :maxdepth: 2
   :glob:

   operations/*
