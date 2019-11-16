Postgresql
----------

:code:`postgresql_databases`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    host.fact.postgresql_databases(postgresql_user=None, postgresql_password=None, postgresql_host=None, postgresql_port=None)


Returns a dict of PostgreSQL databases and metadata:

.. code:: python

    "pyinfra_stuff": {
        "encoding": "UTF8",
        "collate": "en_US.UTF-8",
        "ctype": "en_US.UTF-8",
        ...
    },
    ...



:code:`postgresql_roles`
~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    host.fact.postgresql_roles(postgresql_user=None, postgresql_password=None, postgresql_host=None, postgresql_port=None)


Returns a dict of PostgreSQL roles and data:

.. code:: python

    'pyinfra': {
        'super': true,
        'createrole': false,
        'createdb': false,
        ...
    },
    ...


