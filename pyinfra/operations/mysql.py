'''
Manage MySQL databases, users and privileges.

Requires the ``mysql`` CLI executable on the target host(s).

All operations in this module take four optional global arguments:
    + ``mysql_user``: the username to connect to mysql to
    + ``mysql_password``: the password for the connecting user
    + ``mysql_host``: the hostname of the server to connect to
    + ``mysql_port``: the port of the server to connect to

See the example/mysql.py

'''

import six

from pyinfra.api import MaskString, operation, OperationError, StringCommand
from pyinfra.facts.mysql import make_execute_mysql_command, make_mysql_command


@operation
def sql(
    sql,
    database=None,
    # Details for speaking to MySQL via `mysql` CLI
    mysql_user=None, mysql_password=None,
    mysql_host=None, mysql_port=None,
    state=None, host=None,
):
    '''
    Execute arbitrary SQL against MySQL.

    + sql: SQL command(s) to execute
    + database: optional database to open the connection with
    + mysql_*: global module arguments, see above
    '''

    yield make_execute_mysql_command(
        sql,
        database=database,
        user=mysql_user,
        password=mysql_password,
        host=mysql_host,
        port=mysql_port,
    )


@operation
def user(
    user,
    # Desired user settings
    present=True,
    user_hostname='localhost', password=None, privileges=None,
    # Details for speaking to MySQL via `mysql` CLI via `mysql` CLI
    mysql_user=None, mysql_password=None,
    mysql_host=None, mysql_port=None,
    state=None, host=None,
):
    '''
    Add/remove/update MySQL users.

    + user: the name of the user
    + present: whether the user should exist or not
    + user_hostname: the hostname of the user
    + password: the password of the user (if created)
    + privileges: the global privileges for this user
    + mysql_*: global module arguments, see above

    Hostname:
        this + ``name`` makes the username - so changing this will create a new
        user, rather than update users with the same ``name``.

    Password:
        will only be applied if the user does not exist - ie pyinfra cannot
        detect if the current password doesn't match the one provided, so won't
        attempt to change it.

    Example:

    .. code:: python

        mysql.user(
            name='Create the pyinfra@localhost MySQL user',
            user='pyinfra',
            password='somepassword',
        )
    '''

    current_users = host.fact.mysql_users(
        mysql_user, mysql_password, mysql_host, mysql_port,
    )

    user_host = '{0}@{1}'.format(user, user_hostname)
    is_present = user_host in current_users

    # User not wanted?
    if not present:
        if is_present:
            yield make_execute_mysql_command(
                'DROP USER "{0}"@"{1}"'.format(user, user_hostname),
                user=mysql_user,
                password=mysql_password,
                host=mysql_host,
                port=mysql_port,
            )
        else:
            host.noop('mysql user {0}@{1} does not exist'.format(user, user_hostname))
        return

    # If we want the user and they don't exist
    if present and not is_present:
        sql_bits = ['CREATE USER "{0}"@"{1}"'.format(user, user_hostname)]
        if password:
            sql_bits.append(MaskString('IDENTIFIED BY "{0}"'.format(password)))

        yield make_execute_mysql_command(
            StringCommand(*sql_bits),
            user=mysql_user,
            password=mysql_password,
            host=mysql_host,
            port=mysql_port,
        )
    else:
        host.noop('mysql user {0}@{1} exists'.format(user, user_hostname))

    # If we're here either the user exists or we just created them; either way
    # now we can check any privileges are set.
    if privileges:
        yield _privileges(
            user, privileges,
            user_hostname=user_hostname,
            mysql_user=mysql_user, mysql_password=mysql_password,
            mysql_host=mysql_host, mysql_port=mysql_port,
            state=state, host=host,
        )


@operation
def database(
    database,
    # Desired database settings
    present=True,
    collate=None, charset=None,
    user=None, user_hostname='localhost', user_privileges='ALL',
    # Details for speaking to MySQL via `mysql` CLI
    mysql_user=None, mysql_password=None,
    mysql_host=None, mysql_port=None,
    state=None, host=None,
):
    '''
    Add/remove MySQL databases.

    + name: the name of the database
    + present: whether the database should exist or not
    + collate: the collate to use when creating the database
    + charset: the charset to use when creating the database
    + user: MySQL user to grant privileges on this database to
    + user_hostname: the hostname of the MySQL user to grant
    + user_privileges: privileges to grant to any specified user
    + mysql_*: global module arguments, see above

    Collate/charset:
        these will only be applied if the database does not exist - ie pyinfra
        will not attempt to alter the existing databases collate/character sets.

    Example:

    .. code:: python

        mysql.database(
            name='Create the pyinfra_stuff database',
            database='pyinfra_stuff',
            user='pyinfra',
            user_privileges=['SELECT', 'INSERT'],
            charset='utf8',
        )
    '''

    current_databases = host.fact.mysql_databases(
        mysql_user, mysql_password,
        mysql_host, mysql_port,
    )

    is_present = database in current_databases

    if not present:
        if is_present:
            yield make_execute_mysql_command(
                'DROP DATABASE {0}'.format(database),
                user=mysql_user,
                password=mysql_password,
                host=mysql_host,
                port=mysql_port,
            )
        else:
            host.noop('mysql database {0} does not exist'.format(database))
        return

    # We want the database but it doesn't exist
    if present and not is_present:
        sql_bits = ['CREATE DATABASE {0}'.format(database)]

        if collate:
            sql_bits.append('COLLATE {0}'.format(collate))

        if charset:
            sql_bits.append('CHARSET {0}'.format(charset))

        yield make_execute_mysql_command(
            ' '.join(sql_bits),
            user=mysql_user,
            password=mysql_password,
            host=mysql_host,
            port=mysql_port,
        )
    else:
        host.noop('mysql database {0} exists'.format(database))

    # Ensure any user privileges for this database
    if user and user_privileges:
        yield privileges(
            user,
            user_hostname=user_hostname,
            privileges=user_privileges,
            database=database,
            state=state,
            host=host,
        )


@operation
def privileges(
    user, privileges,
    user_hostname='localhost',
    database='*', table='*',
    present=True,
    flush=True,
    # Details for speaking to MySQL via `mysql` CLI
    mysql_user=None, mysql_password=None,
    mysql_host=None, mysql_port=None,
    state=None, host=None,
):
    '''
    Add/remove MySQL privileges for a user, either global, database or table specific.

    + user: name of the user to manage privileges for
    + privileges: list of privileges the user should have
    + user_hostname: the hostname of the user
    + database: name of the database to grant privileges to (defaults to all)
    + table: name of the table to grant privileges to (defaults to all)
    + present: whether these privileges should exist (False to ``REVOKE)
    + flush: whether to flush (and update) the privileges table after any changes
    + mysql_*: global module arguments, see above
    '''

    # Ensure we have a list
    if isinstance(privileges, six.string_types):
        privileges = [privileges]

    if database != '*':
        database = '`{0}`'.format(database)

    if table != '*':
        table = '`{0}`'.format(table)

        # We can't set privileges on *.tablename as MySQL won't allow it
        if database == '*':
            raise OperationError((
                'Cannot apply MySQL privileges on {0}.{1}, no database provided'
            ).format(database, table))

    database_table = '{0}.{1}'.format(database, table)
    user_grants = host.fact.mysql_user_grants(
        user, user_hostname,
        mysql_user, mysql_password,
        mysql_host, mysql_port,
    )

    has_privileges = False

    if database_table in user_grants:
        existing_privileges = [
            'ALL' if privilege == 'ALL PRIVILEGES' else privilege
            for privilege in user_grants[database_table]['privileges']
        ]

        has_privileges = (
            database_table in user_grants
            and all(
                privilege in existing_privileges
                for privilege in privileges
            )
        )

    target = action = None

    # No privilege and we want it
    if present:
        if not has_privileges:
            action = 'GRANT'
            target = 'TO'
        else:
            host.noop('mysql privileges exist')
            return

    # Permission we don't want
    if not present:
        if has_privileges:
            action = 'REVOKE'
            target = 'FROM'
        else:
            host.noop('mysql privileges do not exist')
            return

    if target and action:
        command = (
            '{action} {privileges} '
            'ON {database}.{table} '
            '{target} "{user}"@"{user_hostname}"'
        ).format(
            privileges=', '.join(privileges),
            action=action, target=target,
            database=database, table=table,
            user=user, user_hostname=user_hostname,
        )

        yield make_execute_mysql_command(
            command,
            user=mysql_user,
            password=mysql_password,
            host=mysql_host,
            port=mysql_port,
        )

        if flush:
            yield make_execute_mysql_command(
                'FLUSH PRIVILEGES',
                user=mysql_user,
                password=mysql_password,
                host=mysql_host,
                port=mysql_port,
            )

_privileges = privileges  # noqa: E305 (for use where kwarg is the same)


@operation
def dump(
    dest, database=None,
    # Details for speaking to MySQL via `mysql` CLI
    mysql_user=None, mysql_password=None,
    mysql_host=None, mysql_port=None,
    state=None, host=None,
):
    '''
    Dump a MySQL database into a ``.sql`` file. Requires ``mysqldump``.

    + dest: name of the file to dump the SQL to
    + database: name of the database to dump
    + mysql_*: global module arguments, see above

    Example:

    .. code:: python

        mysql.dump(
            name='Dump the pyinfra_stuff database',
            dest='/tmp/pyinfra_stuff.dump',
            database='pyinfra_stuff',
        )
    '''

    yield '{0} > {1}'.format(make_mysql_command(
        executable='mysqldump',
        database=database,
        user=mysql_user,
        password=mysql_password,
        host=mysql_host,
        port=mysql_port,
    ), dest)


@operation
def load(
    src, database=None,
    # Details for speaking to MySQL via `mysql` CLI
    mysql_user=None, mysql_password=None,
    mysql_host=None, mysql_port=None,
    state=None, host=None,
):
    '''
    Load ``.sql`` file into a database.

    + src: the filename to read from
    + database: name of the database to import into
    + mysql_*: global module arguments, see above

    Example:

    .. code:: python

        mysql.load(
            name='Import the pyinfra_stuff dump into pyinfra_stuff_copy',
            src='/tmp/pyinfra_stuff.dump',
            database='pyinfra_stuff_copy',
        )
    '''

    yield '{0} < {1}'.format(make_mysql_command(
        database=database,
        user=mysql_user,
        password=mysql_password,
        host=mysql_host,
        port=mysql_port,
    ), src)
