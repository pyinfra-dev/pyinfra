API Reference
=============

The pyinfra API is designed to be used as follows:

1. Create the state we are going to operate on, this consists of:
    - An inventory ``pyinfra.api.Inventory`` containing hosts ``pyinfra.api.Host``, plus any data
    - A config ``pyinfra.api.Config`` for global flag
    - A state ``pyinfra.api.State`` that combines the inventory & config
2. Now state is setup, we define operations:
    - ``pyinfra.api.operation.add_op``
    - ``pyinfra.api.add_deploy``
3. Now that's done, we execute it:
    - ``pyinfra.api.operations.run_ops``

Currently the best example of this in action is in `pyinfra's own main.py <https://github.com/pyinfra-dev/pyinfra/blob/3.x/pyinfra_cli/main.py>`_.

.. toctree::
    :caption: Core API
    :maxdepth: 1
    :glob:

    ../apidoc/*
