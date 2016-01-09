API Reference
=============

The pyinfra API is build like this:

+ A set of Classes storing state
    - ``pyinfra.api.Inventory``
    - ``pyinfra.apiState``
    - ``pyinfra.apiHost``
    - ``pyinfra.apiConfig``
+ Which are passed to functional SSH and operation modules
    - ``operation.py`` & ``operations.py``
    - ``ssh.py``
+ Facts API in ``facts.py``

.. toctree::
    :maxdepth: 1
    :glob:

    api/*
