Postgresql
----------


The PostgreSQL modules manage PostgreSQL databases, users and privileges.

Requires the ``psql`` CLI executable on the target host(s).

All operations in this module take four optional global arguments:
    + ``postgresql_user``: the username to connect to postgresql to
    + ``postgresql_password``: the password for the connecting user
    + ``postgresql_host``: the hostname of the server to connect to
    + ``postgresql_port``: the port of the server to connect to

:code:`postgresql.database`
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add/remove PostgreSQL databases.

.. code:: python

    postgresql.database(
        name, present=True, owner=None, template=None, encoding=None, lc_collate=None,
        lc_ctype=None, tablespace=None, connection_limit=None, postgresql_user=None,
        postgresql_password=None, postgresql_host=None, postgresql_port=None
    )

+ **name**: name of the database
+ **present**: whether the database should exist or not
+ **owner**: the PostgreSQL role that owns the database
+ **template**: name of the PostgreSQL template to use
+ **encoding**: encoding of the database
+ **lc_collate**: lc_collate of the database
+ **lc_ctype**: lc_ctype of the database
+ **tablespace**: the tablespace to use for the template
+ **connection_limit**: the connection limit to apply to the database
+ **postgresql_***: global module arguments, see above

Updates:
    pyinfra will not attempt to change existing databases - it will either
    create or drop databases, but not alter them (if the db exists this
    operation will make no changes).


:code:`postgresql.dump`
~~~~~~~~~~~~~~~~~~~~~~~

Dump a PostgreSQL database into a ``.sql`` file. Requires ``mysqldump``.

.. code:: python

    postgresql.dump(
        remote_filename, database=None, postgresql_user=None, postgresql_password=None,
        postgresql_host=None, postgresql_port=None
    )

+ **database**: name of the database to dump
+ **remote_filename**: name of the file to dump the SQL to
+ **postgresql_***: global module arguments, see above


:code:`postgresql.load`
~~~~~~~~~~~~~~~~~~~~~~~

Load ``.sql`` file into a database.

.. code:: python

    postgresql.load(
        remote_filename, database=None, postgresql_user=None, postgresql_password=None,
        postgresql_host=None, postgresql_port=None
    )

+ **database**: name of the database to import into
+ **remote_filename**: the filename to read from
+ **postgresql_***: global module arguments, see above


:code:`postgresql.role`
~~~~~~~~~~~~~~~~~~~~~~~

Add/remove PostgreSQL roles.

.. code:: python

    postgresql.role(
        name, present=True, password=None, login=True, superuser=False, inherit=False,
        createdb=False, createrole=False, replication=False, connection_limit=None,
        postgresql_user=None, postgresql_password=None, postgresql_host=None,
        postgresql_port=None
    )

+ **name**: name of the role
+ **present**: whether the role should be present or absent
+ **login**: whether the role can login
+ **superuser**: whether role will be a superuser
+ **inherit**: whether the role inherits from other roles
+ **createdb**: whether the role is allowed to create databases
+ **createrole**: whether the role is allowed to create new roles
+ **replication**: whether this role is allowed to replicate
+ **connection_limit**: the connection limit for the role
+ **postgresql_***: global module arguments, see above

Updates:
    pyinfra will not attempt to change existing roles - it will either
    create or drop roles, but not alter them (if the role exists this
    operation will make no changes).


:code:`postgresql.sql`
~~~~~~~~~~~~~~~~~~~~~~

Execute arbitrary SQL against PostgreSQL.

.. code:: python

    postgresql.sql(
        sql, database=None, postgresql_user=None, postgresql_password=None, postgresql_host=None,
        postgresql_port=None
    )

+ **sql**: SQL command(s) to execute
+ **database**: optional database to execute against
+ **postgresql_***: global module arguments, see above

