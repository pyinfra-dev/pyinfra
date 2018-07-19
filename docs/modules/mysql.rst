Mysql
-----


Manage MySQL databases, users and permissions.

Requires the ``mysql`` CLI executable on the target host(s).

All operations in this module take four optional global arguments:
    + ``mysql_user``: the username to connect to mysql to
    + ``mysql_password``: the password for the connecting user
    + ``mysql_host``: the hostname of the server to connect to
    + ``mysql_port``: the port of the server to connect to

:code:`mysql.database`
~~~~~~~~~~~~~~~~~~~~~~

Manage the state of MySQL databases.

.. code:: python

    mysql.database(
        name, present=True, collate=None, charset=None, user=None, user_hostname='localhost',
        user_permissions='ALL', mysql_user=None, mysql_password=None, mysql_host=None,
        mysql_port=None
    )

+ **name**: the name of the database
+ **present**: whether the database should exist or not
+ **collate**: the collate to use when creating the database
+ **charset**: the charset to use when creating the database
+ **user**: MySQL user to grant privileges on this database to
+ **user_hostname**: the hostname of the MySQL user to grant
+ **user_permissions**: permissions to grant to any specified user
+ **mysql_***: global module arguments, see above

Collate/charset:
    these will only be applied if the database does not exist - ie pyinfra
    will not attempt to alter the existing databases collate/character sets.


:code:`mysql.dump`
~~~~~~~~~~~~~~~~~~

Dump a MySQL database into a ``.sql`` file. Requires ``mysqldump``.

.. code:: python

    mysql.dump(
        database, remote_filename, mysql_user=None, mysql_password=None, mysql_host=None,
        mysql_port=None
    )

+ **database**: name of the database to dump
+ **remote_filename**: name of the file to dump the SQL to
+ **mysql_***: global module arguments, see above


:code:`mysql.load`
~~~~~~~~~~~~~~~~~~

Load ``.sql`` file into a database.

.. code:: python

    mysql.load(
        database, remote_filename, mysql_user=None, mysql_password=None, mysql_host=None,
        mysql_port=None
    )

+ **database**: name of the database to import into
+ **remote_filename**: the filename to read from
+ **mysql_***: global module arguments, see above


:code:`mysql.permission`
~~~~~~~~~~~~~~~~~~~~~~~~

Manage MySQL permissions for a user, either global, database or table specific.

.. code:: python

    mysql.permission(
        user, permissions, user_hostname='localhost', database='*', table='*', present=True,
        flush=True, mysql_user=None, mysql_password=None, mysql_host=None, mysql_port=None
    )

+ **user**: name of the user to manage permissions for
+ **permissions**: list of permissions the user should have
+ **user_hostname**: the hostname of the user
+ **database**: name of the database to grant user permissions to (defaults to all)
+ **table**: name of the table to grant user permissions to (defaults to all)
+ **present**: whether these permissions should exist (False to ``REVOKE)
+ **flush**: whether to flush (and update) the permissions table after any changes
+ **mysql_***: global module arguments, see above


:code:`mysql.sql`
~~~~~~~~~~~~~~~~~

Execute arbitrary SQL against MySQL.

.. code:: python

    mysql.sql(sql, database=None, mysql_user=None, mysql_password=None, mysql_host=None, mysql_port=None)

+ **sql**: the SQL to send to MySQL
+ **database**: optional database to open the connection with
+ **mysql_***: global module arguments, see above


:code:`mysql.user`
~~~~~~~~~~~~~~~~~~

Manage the state of MySQL users.

.. code:: python

    mysql.user(
        name, present=True, user_hostname='localhost', password=None, permissions=None,
        mysql_user=None, mysql_password=None, mysql_host=None, mysql_port=None
    )

+ **name**: the name of the user
+ **present**: whether the user should exist or not
+ **user_hostname**: the hostname of the user
+ **password**: the password of the user (if created)
+ **permissions**: the global permissions for this user
+ **mysql_***: global module arguments, see above

Hostname:
    this + ``name`` makes the username - so changing this will create a new
    user, rather than update users with the same ``name``.

Password:
    will only be applied if the user does not exist - ie pyinfra cannot
    detect if the current password doesn't match the one provided, so won't
    attempt to change it.

