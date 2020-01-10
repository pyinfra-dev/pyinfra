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

from pyinfra.api import operation
from pyinfra.facts.postgresql import make_execute_psql_command, make_psql_command


@operation
def sql(
    state, host, sql,
    database=None,
    # Details for speaking to PostgreSQL via `psql` CLI
    postgresql_user=None, postgresql_password=None,
    postgresql_host=None, postgresql_port=None,
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
    state, host, name,
    present=True,
    password=None, login=True, superuser=False, inherit=False,
    createdb=False, createrole=False, replication=False, connection_limit=None,
    # Details for speaking to PostgreSQL via `psql` CLI
    postgresql_user=None, postgresql_password=None,
    postgresql_host=None, postgresql_port=None,
):
    '''
    Add/remove PostgreSQL roles.

    + name: name of the role
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
            {'Create the pyinfra PostgreSQL role'},
            'pyinfra',
            password='somepassword',
            superuser=True,
            login=True,
            sudo_user='postgres',
        )

    '''

    roles = host.fact.postgresql_roles(
        postgresql_user, postgresql_password,
        postgresql_host, postgresql_port,
    )

    is_present = name in roles

    # User not wanted?
    if not present:
        if is_present:
            yield make_execute_psql_command(
                'DROP ROLE {0}'.format(name),
                user=postgresql_user,
                password=postgresql_password,
                host=postgresql_host,
                port=postgresql_port,
            )
        return

    # If we want the user and they don't exist
    if not is_present:
        sql_bits = ['CREATE ROLE {0}'.format(name)]

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
            sql_bits.append("PASSWORD '{0}'".format(password))

        yield make_execute_psql_command(
            ' '.join(sql_bits),
            user=postgresql_user,
            password=postgresql_password,
            host=postgresql_host,
            port=postgresql_port,
        )


@operation
def database(
    state, host, name,
    present=True, owner=None,
    template=None, encoding=None,
    lc_collate=None, lc_ctype=None, tablespace=None,
    connection_limit=None,
    # Details for speaking to PostgreSQL via `psql` CLI
    postgresql_user=None, postgresql_password=None,
    postgresql_host=None, postgresql_port=None,
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
            {'Create the pyinfra_stuff database'},
            'pyinfra_stuff',
            owner='pyinfra',
            encoding='UTF8',
            sudo_user='postgres',
        )

    '''

    current_databases = host.fact.postgresql_databases(
        postgresql_user, postgresql_password,
        postgresql_host, postgresql_port,
    )

    is_present = name in current_databases

    if not present:
        if is_present:
            yield make_execute_psql_command(
                'DROP DATABASE {0}'.format(name),
                user=postgresql_user,
                password=postgresql_password,
                host=postgresql_host,
                port=postgresql_port,
            )
        return

    # We want the database but it doesn't exist
    if present and not is_present:
        sql_bits = ['CREATE DATABASE {0}'.format(name)]

        for key, value in (
            ('OWNER', owner),
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
            ' '.join(sql_bits),
            user=postgresql_user,
            password=postgresql_password,
            host=postgresql_host,
            port=postgresql_port,
        )


@operation
def dump(
    state, host,
    remote_filename, database=None,
    # Details for speaking to PostgreSQL via `psql` CLI
    postgresql_user=None, postgresql_password=None,
    postgresql_host=None, postgresql_port=None,
):
    '''
    Dump a PostgreSQL database into a ``.sql`` file. Requires ``pg_dump``.

    + database: name of the database to dump
    + remote_filename: name of the file to dump the SQL to
    + postgresql_*: global module arguments, see above

    Example:

    .. code:: python

        postgresql.dump(
            {'Dump the pyinfra_stuff database'},
            '/tmp/pyinfra_stuff.dump',
            database='pyinfra_stuff',
            sudo_user='postgres',
        )

    '''

    yield '{0} > {1}'.format(make_psql_command(
        executable='pg_dump',
        database=database,
        user=postgresql_user,
        password=postgresql_password,
        host=postgresql_host,
        port=postgresql_port,
    ), remote_filename)


@operation
def load(
    state, host,
    remote_filename, database=None,
    # Details for speaking to PostgreSQL via `psql` CLI
    postgresql_user=None, postgresql_password=None,
    postgresql_host=None, postgresql_port=None,
):
    '''
    Load ``.sql`` file into a database.

    + database: name of the database to import into
    + remote_filename: the filename to read from
    + postgresql_*: global module arguments, see above

    Example:

    .. code:: python

        postgresql.load(
            {'Import the pyinfra_stuff dump into pyinfra_stuff_copy'},
            '/tmp/pyinfra_stuff.dump',
            database='pyinfra_stuff_copy',
            sudo_user='postgres',
        )

    '''

    yield '{0} < {1}'.format(make_psql_command(
        database=database,
        user=postgresql_user,
        password=postgresql_password,
        host=postgresql_host,
        port=postgresql_port,
    ), remote_filename)
