Operations Index
================

Operations are used to describe changes to make to systems in the inventory. Use them to define state and pyinfra will make any necessary changes to reach that state. All operations accept a set of :doc:`global arguments <arguments>` and are grouped as Python modules.

**Want a new operation?** Check out :doc:`the writing operations guide <./api/operations>`.

.. raw:: html

   <h3>Popular operations by category</h3>

.. admonition:: Basics
   :class: note inline

   :doc:`operations/files`, :doc:`operations/server`, :doc:`operations/git`, :doc:`operations/systemd`

.. admonition:: System Packages
   :class: note inline

   :doc:`operations/apt`, :doc:`operations/apk`, :doc:`operations/brew`, :doc:`operations/dnf`, :doc:`operations/yum`

.. admonition:: Language Packages
   :class: note inline

   :doc:`operations/gem`, :doc:`operations/npm`, :doc:`operations/pip`

.. admonition:: Databases
   :class: note inline

   :doc:`operations/postgresql`, :doc:`operations/mysql`

.. raw:: html

   <h3>All operations alphabetically</h3>

.. raw:: html

   <style type="text/css">
      #operations-index .toctree-wrapper > ul {
         padding: 0;
      }
      #operations-index .toctree-wrapper > ul > li {
         padding: 0;
         list-style: none;
         margin: 20px 0;
      }
      #operations-index .toctree-wrapper > ul > li > ul > li {
         display: inline-block;
      }
   </style>

.. toctree::
   :maxdepth: 2
   :glob:

   operations/*
