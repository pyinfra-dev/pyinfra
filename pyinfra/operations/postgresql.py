'''
The PostgreSQL modules manage PostgreSQL databases, users and privileges.

Requires the ``psql`` CLI executable on the target host(s).

All operations in this module take four optional global arguments:
    + ``postgresql_user``: the username to connect to postgresql to
    + ``postgresql_password``: the password for the connecting user
    + ``postgresql_host``: the hostname of the server to connect to
    + ``postgresql_port``: the port of the server to connect to

See example/postgresql.py for detailed example

'''

from pyinfra.api import MaskString, operation, StringCommand
from pyinfra.facts.postgresql import (
    make_execute_psql_command,
    make_psql_command,
    PostgresqlDatabases,
    PostgresqlRoles,
)


@operation(is_idempotent=False)
def sql(
    sql,
    database=None,
    # Details for speaking to PostgreSQL via `psql` CLI
    postgresql_user=None, postgresql_password=None,
    postgresql_host=None, postgresql_port=None,
    state=None, host=None,
):
    '''
    Execute arbitrary SQL against PostgreSQL.

    + sql: SQL command(s) to execute
    + database: optional database to execute against
    + postgresql_*: global module arguments, see above
    '''

    yield make_execute_psql_command(
        sql,
        database=database,
        user=postgresql_user,
        password=postgresql_password,
        host=postgresql_host,
        port=postgresql_port,
    )


@operation
def role(
    role,
    present=True,
    password=None, login=True, superuser=False, inherit=False,
    createdb=False, createrole=False, replication=False, connection_limit=None,
    # Details for speaking to PostgreSQL via `psql` CLI
    postgresql_user=None, postgresql_password=None,
    postgresql_host=None, postgresql_port=None,
    state=None, host=None,
):
    '''
    Add/remove PostgreSQL roles.

    + role: name of the role
    + present: whether the role should be present or absent
    + password: the password for the role
    + login: whether the role can login
    + superuser: whether role will be a superuser
    + inherit: whether the role inherits from other roles
    + createdb: whether the role is allowed to create databases
    + createrole: whether the role is allowed to create new roles
    + replication: whether this role is allowed to replicate
    + connection_limit: the connection limit for the role
    + postgresql_*: global module arguments, see above

    Updates:
        pyinfra will not attempt to change existing roles - it will either
        create or drop roles, but not alter them (if the role exists this
        operation will make no changes).

    Example:

    .. code:: python

        postgresql.role(
            name='Create the pyinfra PostgreSQL role',
            role='pyinfra',
            password='somepassword',
            superuser=True,
            login=True,
            sudo_user='postgres',
        )

    '''

    roles = host.get_fact(
        PostgresqlRoles,
        postgresql_user=postgresql_user,
        postgresql_password=postgresql_password,
        postgresql_host=postgresql_host,
        postgresql_port=postgresql_port,
    )

    is_present = role in roles

    # User not wanted?
    if not present:
        if is_present:
            yield make_execute_psql_command(
                'DROP ROLE "{0}"'.format(role),
                user=postgresql_user,
                password=postgresql_password,
                host=postgresql_host,
                port=postgresql_port,
            )
        else:
            host.noop('postgresql role {0} does not exist'.format(role))
        return

    # If we want the user and they don't exist
    if not is_present:
        sql_bits = ['CREATE ROLE "{0}"'.format(role)]

        for key, value in (
            ('LOGIN', login),
            ('SUPERUSER', superuser),
            ('INHERIT', inherit),
            ('CREATEDB', createdb),
            ('CREATEROLE', createrole),
            ('REPLICATION', replication),
        ):
            if value:
                sql_bits.append(key)

        if connection_limit:
            sql_bits.append('CONNECTION LIMIT {0}'.format(connection_limit))

        if password:
            sql_bits.append(MaskString("PASSWORD '{0}'".format(password)))

        yield make_execute_psql_command(
            StringCommand(*sql_bits),
            user=postgresql_user,
            password=postgresql_password,
            host=postgresql_host,
            port=postgresql_port,
        )
    else:
        host.noop('postgresql role {0} exists'.format(role))


@operation
def database(
    database,
    present=True, owner=None,
    template=None, encoding=None,
    lc_collate=None, lc_ctype=None, tablespace=None,
    connection_limit=None,
    # Details for speaking to PostgreSQL via `psql` CLI
    postgresql_user=None, postgresql_password=None,
    postgresql_host=None, postgresql_port=None,
    state=None, host=None,
):
    '''
    Add/remove PostgreSQL databases.

    + name: name of the database
    + present: whether the database should exist or not
    + owner: the PostgreSQL role that owns the database
    + template: name of the PostgreSQL template to use
    + encoding: encoding of the database
    + lc_collate: lc_collate of the database
    + lc_ctype: lc_ctype of the database
    + tablespace: the tablespace to use for the template
    + connection_limit: the connection limit to apply to the database
    + postgresql_*: global module arguments, see above

    Updates:
        pyinfra will not attempt to change existing databases - it will either
        create or drop databases, but not alter them (if the db exists this
        operation will make no changes).

    Example:

    .. code:: python

        postgresql.database(
            name='Create the pyinfra_stuff database',
            database='pyinfra_stuff',
            owner='pyinfra',
            encoding='UTF8',
            sudo_user='postgres',
        )

    '''

    current_databases = host.get_fact(
        PostgresqlDatabases,
        postgresql_user=postgresql_user,
        postgresql_password=postgresql_password,
        postgresql_host=postgresql_host,
        postgresql_port=postgresql_port,
    )

    is_present = database in current_databases

    if not present:
        if is_present:
            yield make_execute_psql_command(
                'DROP DATABASE "{0}"'.format(database),
                user=postgresql_user,
                password=postgresql_password,
                host=postgresql_host,
                port=postgresql_port,
            )
        else:
            host.noop('postgresql database {0} does not exist'.format(database))
        return

    # We want the database but it doesn't exist
    if present and not is_present:
        sql_bits = ['CREATE DATABASE "{0}"'.format(database)]

        for key, value in (
            ('OWNER', '"{0}"'.format(owner) if owner else owner),
            ('TEMPLATE', template),
            ('ENCODING', encoding),
            ('LC_COLLATE', lc_collate),
            ('LC_CTYPE', lc_ctype),
            ('TABLESPACE', tablespace),
            ('CONNECTION LIMIT', connection_limit),
        ):
            if value:
                sql_bits.append('{0} {1}'.format(key, value))

        yield make_execute_psql_command(
            StringCommand(*sql_bits),
            user=postgresql_user,
            password=postgresql_password,
            host=postgresql_host,
            port=postgresql_port,
        )
    else:
        host.noop('postgresql database {0} exists'.format(database))


@operation(is_idempotent=False)
def dump(
    dest, database=None,
    # Details for speaking to PostgreSQL via `psql` CLI
    postgresql_user=None, postgresql_password=None,
    postgresql_host=None, postgresql_port=None,
    state=None, host=None,
):
    '''
    Dump a PostgreSQL database into a ``.sql`` file. Requires ``pg_dump``.

    + dest: name of the file to dump the SQL to
    + database: name of the database to dump
    + postgresql_*: global module arguments, see above

    Example:

    .. code:: python

        postgresql.dump(
            name='Dump the pyinfra_stuff database',
            dest='/tmp/pyinfra_stuff.dump',
            database='pyinfra_stuff',
            sudo_user='postgres',
        )

    '''

    yield StringCommand(make_psql_command(
        executable='pg_dump',
        database=database,
        user=postgresql_user,
        password=postgresql_password,
        host=postgresql_host,
        port=postgresql_port,
    ), '>', dest)


@operation(is_idempotent=False)
def load(
    src, database=None,
    # Details for speaking to PostgreSQL via `psql` CLI
    postgresql_user=None, postgresql_password=None,
    postgresql_host=None, postgresql_port=None,
    state=None, host=None,
):
    '''
    Load ``.sql`` file into a database.

    + src: the filename to read from
    + database: name of the database to import into
    + postgresql_*: global module arguments, see above

    Example:

    .. code:: python

        postgresql.load(
            name='Import the pyinfra_stuff dump into pyinfra_stuff_copy',
            src='/tmp/pyinfra_stuff.dump',
            database='pyinfra_stuff_copy',
            sudo_user='postgres',
        )

    '''

    yield StringCommand(make_psql_command(
        database=database,
        user=postgresql_user,
        password=postgresql_password,
        host=postgresql_host,
        port=postgresql_port,
    ), '<', src)
