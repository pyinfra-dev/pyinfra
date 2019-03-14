pyinfra uses facts to determine the existing state of a remote server. Operations use this information to generate commands which alter the state. Facts can be executed/tested via the command line:

.. code:: sh

    pyinfra myhost.com fact date another_fact ...

Or as part of :doc:`a deploy <deploys>`:

.. code:: py

    if host.fact.linux_name == 'Ubuntu':
        apt.packages(...)

All The Facts
_____________

Facts, like :doc:`operations <operations>`, are namespaced as different modules - shortcuts to each of these can be found in the sidebar.
