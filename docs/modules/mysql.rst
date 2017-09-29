Mysql
-----


Manage MySQL databases, users and permissions.

:code:`mysql.database`
~~~~~~~~~~~~~~~~~~~~~~

Manage the state of MySQL databases.

.. code:: python

    mysql.database(name, collate=None, charset=None, user=None, user_permissions='ALL', present=True)

+ **name**: the name of the database
+ **collate**: the collate to use when creating the database
+ **charset**: the charset to use when creating the database
+ **user**: MySQL user to grant privileges on this database to
+ **user_permissions**: permissions to grant the user
+ **present**: whether the database should exist or not

Collate/charset:
    these will only be applied if the database does not exist - ie pyinfra
    will not attempt to alter the existing databases collate/character sets.


:code:`mysql.permission`
~~~~~~~~~~~~~~~~~~~~~~~~

Manage MySQL permissions for users, either global or table specific.

.. code:: python

    mysql.permission(user, permissions, table=None)

+ **user**: name of the user to manage permissions for
+ **permissions**: list of permissions the user should have
+ **table**: name of the table to grant user permissions to (defaults to global)


:code:`mysql.sql`
~~~~~~~~~~~~~~~~~

Execute arbitrary SQL against MySQL.

.. code:: python

    mysql.sql(sql, database=None)

+ **sql**: the SQL to send to MySQL
+ **database**: optional database to open the connection with


:code:`mysql.user`
~~~~~~~~~~~~~~~~~~

Manage the state of MySQL uusers.

.. code:: python

    mysql.user(name, hostname='localhost', password=None, permissions=None, present=True)

+ **name**: the name of the user
+ **hostname**: the hostname of the user
+ **password**: the password of the user (if created)
+ **permissions**: the global permissions for this user
+ **present**: whether the user should exist or not

