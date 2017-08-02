Packaging Deploys
=================

Operations represent low-level state that should be met and applied if needed. Deploys are more high-level, for example "install & configure service X". They represent a collection of operations. Like operations, deploys can be made into python packages making them reusable and shareable.

Writing a deploy is similar to :doc:`writing an operation <api/modules>`:

.. code:: py

    from pyinfra.api import deploy
    from pyinfra.modules import apt

    @deploy('Install MariaDB')
    def install_mariadb(state, host):
        apt.packages(
            {'Install MariaDB apt package'},
            state, host,
            'mariadb-server',
        )
