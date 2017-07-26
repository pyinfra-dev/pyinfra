API Reference
=============

The pyinfra API is designed like this:

+ A set of classes storing state
    - ``pyinfra.api.State``
    - ``pyinfra.api.Inventory``
    - ``pyinfra.api.Host``
    - ``pyinfra.api.Config``
+ A set of modules that implement functionality:
    - ``operation.py`` & ``operations.py``
    - ``ssh.py``
    - ``facts.py``


.. toctree::
    :caption: Core API
    :maxdepth: 1
    :glob:

    ../apidoc/*
