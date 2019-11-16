Mysql
-----

:code:`mysql_databases`
~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    host.fact.mysql_databases(mysql_user=None, mysql_password=None, mysql_host=None, mysql_port=None)


Returns a dict of existing MySQL databases and associated data:

.. code:: python

    'mysql': {
        'character_set': 'latin1',
        'collation_name': 'latin1_swedish_ci'
    },
    ...



:code:`mysql_user_grants`
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    host.fact.mysql_user_grants(user, hostname='localhost', mysql_user=None, mysql_password=None, mysql_host=None, mysql_port=None)


Returns a dict of ``<database>`.<table>`` with granted privileges for each:

.. code:: python

    '`pyinfra_stuff`.*': {
        'privileges': [
            'SELECT',
            'INSERT'
        ],
        "with_grant_option": false
    },
    ...



:code:`mysql_users`
~~~~~~~~~~~~~~~~~~~

.. code:: python

    host.fact.mysql_users(mysql_user=None, mysql_password=None, mysql_host=None, mysql_port=None)


Returns a dict of MySQL ``user@host``'s and their associated data:

.. code:: python

    'user@host': {
        'privileges': ['Alter', 'Grant'],
        'max_connections': 5,
        ...
    },
    ...


