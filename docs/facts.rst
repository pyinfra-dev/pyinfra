Facts Index
===========

pyinfra uses **facts** to determine the existing state of a remote server. Operations use this information to generate commands which alter the state. Facts are read-only and is populated at the beginning of the deploy.

Facts can be executed/tested via the command line:

.. code:: sh

    # Example how to get multiple facts from a server myhost.com
    pyinfra myhost.com fact server.Date server.Hostname ...

If you want to pass an argument to a fact, pass it with ``key=value``. For example:

.. code:: sh

    # See if the package 'openssh-server' is installed servers myhost.com and myhost2.com
    pyinfra myhost.com,myhost2.com fact deb.DebPackage name=openssh-server

Multiple facts with arguments may be called like so:

.. code:: sh

    pyinfra @local fact files.File path=setup.py files.File path=anotherfile.txt

You can leverage facts as part of :doc:`within operations <using-operations>` like this:

.. code:: py

    from pyinfra import host
    from pyinfra.facts.server import LinuxName

    if host.get_fact(LinuxName) == 'Ubuntu':
        apt.packages(...)

**Want a new fact?** Check out :doc:`the writing facts guide <./api/operations>`.

Facts, like :doc:`operations <operations>`, are namespaced as different modules - shortcuts to each of these can be found in the sidebar.

.. raw:: html

   <style type="text/css">
      #facts-index .toctree-wrapper > ul {
         padding: 0;
      }
      #facts-index .toctree-wrapper > ul > li {
         padding: 0;
         list-style: none;
         margin: 20px 0;
      }
      #facts-index .toctree-wrapper > ul > li > ul > li {
         display: inline-block;
      }
   </style>

.. toctree::
   :maxdepth: 2
   :glob:

   facts/*
