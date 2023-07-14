"""
Manage MySQL databases, users and privileges.

Requires the ``mysql`` CLI executable on the target host(s).

All operations in this module take four optional arguments:
    + ``mysql_user``: the username to connect to mysql to
    + ``mysql_password``: the password for the connecting user
    + ``mysql_host``: the hostname of the server to connect to
    + ``mysql_port``: the port of the server to connect to

See the example/mysql.py

"""

from pyinfra import host
from pyinfra.api import MaskString, OperationError, QuoteString, StringCommand, operation
from pyinfra.facts.mysql import (
    MysqlDatabases,
    MysqlUserGrants,
    MysqlUsers,
    make_execute_mysql_command,
    make_mysql_command,
)


@operation(is_idempotent=False)
def sql(
    sql,
    database=None,
    # Details for speaking to MySQL via `mysql` CLI
    mysql_user=None,
    mysql_password=None,
    mysql_host=None,
    mysql_port=None,
):
    """
    Execute arbitrary SQL against MySQL.

    + sql: SQL command(s) to execute
    + database: optional database to open the connection with
    + mysql_*: global module arguments, see above
    """

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
    present=True,
    user_hostname="localhost",
    password=None,
    privileges=None,
    # MySQL REQUIRE SSL/TLS options
    require=None,  # SSL or X509
    require_cipher=False,
    require_issuer=False,
    require_subject=False,
    # MySQL WITH resource limit options
    max_connections=None,
    max_queries_per_hour=None,
    max_updates_per_hour=None,
    max_connections_per_hour=None,
    # Details for speaking to MySQL via `mysql` CLI via `mysql` CLI
    mysql_user=None,
    mysql_password=None,
    mysql_host=None,
    mysql_port=None,
):
    """
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

    **Example:**

    .. code:: python

        mysql.user(
            name="Create the pyinfra@localhost MySQL user",
            user="pyinfra",
            password="somepassword",
        )

        # Create a user with resource limits
        mysql.user(
            name="Create the pyinfra@localhost MySQL user",
            user="pyinfra",
            max_connections=50,
            max_updates_per_hour=10,
        )

        # Create a user that requires SSL for connections
        mysql.user(
            name="Create the pyinfra@localhost MySQL user",
            user="pyinfra",
            password="somepassword",
            require="SSL",
        )

        # Create a user that requires a specific certificate
        mysql.user(
            name="Create the pyinfra@localhost MySQL user",
            user="pyinfra",
            password="somepassword",
            require="X509",
            require_issuer="/C=SE/ST=Stockholm...",
            require_cipher="EDH-RSA-DES-CBC3-SHA",
        )
    """

    if require and require not in ("SSL", "X509"):
        raise OperationError('Invalid `require` value, must be: "SSL" or "X509"')

    if require != "X509":
        if require_cipher:
            raise OperationError('Cannot set `require_cipher` if `require` is not "X509"')
        if require_issuer:
            raise OperationError('Cannot set `require_issuer` if `require` is not "X509"')
        if require_subject:
            raise OperationError('Cannot set `require_subject` if `require` is not "X509"')

    current_users = host.get_fact(
        MysqlUsers,
        mysql_user=mysql_user,
        mysql_password=mysql_password,
        mysql_host=mysql_host,
        mysql_port=mysql_port,
    )

    user_host = "{0}@{1}".format(user, user_hostname)
    is_present = user_host in current_users

    if not present:
        if is_present:
            yield make_execute_mysql_command(
                'DROP USER "{0}"@"{1}"'.format(user, user_hostname),
                user=mysql_user,
                password=mysql_password,
                host=mysql_host,
                port=mysql_port,
            )
            current_users.pop(user_host)
        else:
            host.noop("mysql user {0}@{1} does not exist".format(user, user_hostname))
        return

    new_or_updated_user_fact = {
        "ssl_type": "ANY" if require == "SSL" else require,
        "ssl_cipher": require_cipher,
        "x509_issuer": require_issuer,
        "x509_subject": require_subject,
        "max_user_connections": max_connections,
        "max_questions": max_queries_per_hour,
        "max_updates": max_updates_per_hour,
        "max_connections": max_connections_per_hour,
    }

    if present and not is_present:
        sql_bits = ['CREATE USER "{0}"@"{1}"'.format(user, user_hostname)]
        if password:
            sql_bits.append(MaskString('IDENTIFIED BY "{0}"'.format(password)))

        if require == "SSL":
            sql_bits.append("REQUIRE SSL")

        if require == "X509":
            sql_bits.append("REQUIRE")
            require_bits = []

            if require_cipher:
                require_bits.append('CIPHER "{0}"'.format(require_cipher))
            if require_issuer:
                require_bits.append('ISSUER "{0}"'.format(require_issuer))
            if require_subject:
                require_bits.append('SUBJECT "{0}"'.format(require_subject))

            if not require_bits:
                require_bits.append("X509")

            sql_bits.extend(require_bits)

        resource_bits = []
        if max_connections:
            resource_bits.append("MAX_USER_CONNECTIONS {0}".format(max_connections))
        if max_queries_per_hour:
            resource_bits.append("MAX_QUERIES_PER_HOUR {0}".format(max_queries_per_hour))
        if max_updates_per_hour:
            resource_bits.append("MAX_UPDATES_PER_HOUR {0}".format(max_updates_per_hour))
        if max_connections_per_hour:
            resource_bits.append("MAX_CONNECTIONS_PER_HOUR {0}".format(max_connections_per_hour))

        if resource_bits:
            sql_bits.append("WITH")
            sql_bits.append(" ".join(resource_bits))

        yield make_execute_mysql_command(
            StringCommand(*sql_bits),
            user=mysql_user,
            password=mysql_password,
            host=mysql_host,
            port=mysql_port,
        )

        current_users[user_host] = new_or_updated_user_fact

    if present and is_present:
        current_user = current_users.get(user_host)

        alter_bits = []

        if require == "SSL":
            if current_user["ssl_type"] != "ANY":
                alter_bits.append("REQUIRE SSL")

        if require == "X509":
            require_bits = []

            if require_cipher and current_user["ssl_cipher"] != require_cipher:
                require_bits.append('CIPHER "{0}"'.format(require_cipher))
            if require_issuer and current_user["x509_issuer"] != require_issuer:
                require_bits.append('ISSUER "{0}"'.format(require_issuer))
            if require_subject and current_user["x509_subject"] != require_subject:
                require_bits.append('SUBJECT "{0}"'.format(require_subject))

            if not require_bits:
                if current_user["ssl_type"] != "X509":
                    require_bits.append("X509")

            if require_bits:
                alter_bits.append("REQUIRE")
                alter_bits.extend(require_bits)

        resource_bits = []
        if max_connections and current_user["max_user_connections"] != max_connections:
            resource_bits.append("MAX_USER_CONNECTIONS {0}".format(max_connections))
        if max_queries_per_hour and current_user["max_questions"] != max_queries_per_hour:
            resource_bits.append("MAX_QUERIES_PER_HOUR {0}".format(max_queries_per_hour))
        if max_updates_per_hour and current_user["max_updates"] != max_updates_per_hour:
            resource_bits.append("MAX_UPDATES_PER_HOUR {0}".format(max_updates_per_hour))
        if max_connections_per_hour and current_user["max_connections"] != max_connections_per_hour:
            resource_bits.append("MAX_CONNECTIONS_PER_HOUR {0}".format(max_connections_per_hour))

        if resource_bits:
            alter_bits.append("WITH")
            alter_bits.append(" ".join(resource_bits))

        if alter_bits:
            sql_bits = ['ALTER USER "{0}"@"{1}"'.format(user, user_hostname)]
            sql_bits.extend(alter_bits)
            yield make_execute_mysql_command(
                StringCommand(*sql_bits),
                user=mysql_user,
                password=mysql_password,
                host=mysql_host,
                port=mysql_port,
            )
            current_user.update(new_or_updated_user_fact)
        else:
            host.noop("mysql user {0}@{1} exists".format(user, user_hostname))

    # If we're here either the user exists or we just created them; either way
    # now we can check any privileges are set.
    if privileges:
        yield from _privileges(
            user,
            privileges,
            user_hostname=user_hostname,
            mysql_user=mysql_user,
            mysql_password=mysql_password,
            mysql_host=mysql_host,
            mysql_port=mysql_port,
        )


@operation
def database(
    database,
    # Desired database settings
    present=True,
    collate=None,
    charset=None,
    user=None,
    user_hostname="localhost",
    user_privileges="ALL",
    # Details for speaking to MySQL via `mysql` CLI
    mysql_user=None,
    mysql_password=None,
    mysql_host=None,
    mysql_port=None,
):
    """
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

    **Example:**

    .. code:: python

        mysql.database(
            name="Create the pyinfra_stuff database",
            database="pyinfra_stuff",
            user="pyinfra",
            user_privileges=["SELECT", "INSERT"],
            charset="utf8",
        )
    """

    current_databases = host.get_fact(
        MysqlDatabases,
        mysql_user=mysql_user,
        mysql_password=mysql_password,
        mysql_host=mysql_host,
        mysql_port=mysql_port,
    )

    is_present = database in current_databases

    if not present:
        if is_present:
            yield make_execute_mysql_command(
                "DROP DATABASE `{0}`".format(database),
                user=mysql_user,
                password=mysql_password,
                host=mysql_host,
                port=mysql_port,
            )
            current_databases.pop(database)
        else:
            host.noop("mysql database {0} does not exist".format(database))
        return

    # We want the database but it doesn't exist
    if present and not is_present:
        sql_bits = ["CREATE DATABASE `{0}`".format(database)]

        if collate:
            sql_bits.append("COLLATE {0}".format(collate))

        if charset:
            sql_bits.append("CHARSET {0}".format(charset))

        yield make_execute_mysql_command(
            " ".join(sql_bits),
            user=mysql_user,
            password=mysql_password,
            host=mysql_host,
            port=mysql_port,
        )
        current_databases[database] = {
            "collate": collate,
            "charset": charset,
        }
    else:
        host.noop("mysql database {0} exists".format(database))

    # Ensure any user privileges for this database
    if user and user_privileges:
        yield from privileges(
            user,
            user_hostname=user_hostname,
            privileges=user_privileges,
            database=database,
            mysql_user=mysql_user,
            mysql_password=mysql_password,
            mysql_host=mysql_host,
            mysql_port=mysql_port,
        )


@operation
def privileges(
    user,
    privileges,
    user_hostname="localhost",
    database="*",
    table="*",
    flush=True,
    with_grant_option=False,
    # Details for speaking to MySQL via `mysql` CLI
    mysql_user=None,
    mysql_password=None,
    mysql_host=None,
    mysql_port=None,
):
    """
    Add/remove MySQL privileges for a user, either global, database or table specific.

    + user: name of the user to manage privileges for
    + privileges: list of privileges the user should have (see also: ``with_grant_option`` argument)
    + user_hostname: the hostname of the user
    + database: name of the database to grant privileges to (defaults to all)
    + table: name of the table to grant privileges to (defaults to all)
    + flush: whether to flush (and update) the privileges table after any changes
    + with_grant_option: whether the grant option privilege should be set
    + mysql_*: global module arguments, see above
    """

    # Ensure we have a list
    if isinstance(privileges, str):
        privileges = {privileges}

    if isinstance(privileges, list):
        privileges = set(privileges)

    if with_grant_option:
        privileges.add("GRANT OPTION")

    if database != "*":
        database = "`{0}`".format(database)

    if table != "*":
        table = "`{0}`".format(table)

        # We can't set privileges on *.tablename as MySQL won't allow it
        if database == "*":
            raise OperationError(
                ("Cannot apply MySQL privileges on {0}.{1}, no database provided").format(
                    database,
                    table,
                ),
            )

    database_table = "{0}.{1}".format(database, table)
    user_grants = host.get_fact(
        MysqlUserGrants,
        user=user,
        hostname=user_hostname,
        mysql_user=mysql_user,
        mysql_password=mysql_password,
        mysql_host=mysql_host,
        mysql_port=mysql_port,
    )

    existing_privileges = set()
    if database_table in user_grants:
        existing_privileges = {
            "ALL" if privilege == "ALL PRIVILEGES" else privilege
            for privilege in user_grants[database_table]
        }
    else:
        user_grants[database_table] = set()

    def handle_privileges(action, target, privileges_to_apply, with_statement=None):
        command = (
            "{action} {privileges} " "ON {database}.{table} " '{target} "{user}"@"{user_hostname}"'
        ).format(
            privileges=", ".join(sorted(privileges_to_apply)),
            action=action,
            target=target,
            database=database,
            table=table,
            user=user,
            user_hostname=user_hostname,
        )

        if with_statement:
            command += " WITH {with_statement}".format(with_statement=with_statement)

        yield make_execute_mysql_command(
            command,
            user=mysql_user,
            password=mysql_password,
            host=mysql_host,
            port=mysql_port,
        )

    # Find / revoke any privileges that exist that do not match the desired state
    privileges_to_revoke = existing_privileges.difference(privileges)
    # Find / grant any privileges that we want but do not exist
    privileges_to_grant = privileges - existing_privileges

    user_grants[database_table] -= privileges_to_revoke
    user_grants[database_table].update(privileges_to_grant)

    if privileges_to_grant:
        # We will grant something on this table, no need to revoke "USAGE" as it will be overridden
        privileges_to_revoke.discard("USAGE")

    if privileges_to_revoke:
        if {"ALL", "GRANT OPTION"} == privileges_to_revoke:
            # This specific case is identified as the alternative syntax for revoke (without ON).
            # To avoid this problem, revoke in 2 steps.
            yield from handle_privileges("REVOKE", "FROM", {"GRANT OPTION"})
            yield from handle_privileges("REVOKE", "FROM", {"ALL PRIVILEGES"})
        else:
            yield from handle_privileges("REVOKE", "FROM", privileges_to_revoke)

    if privileges_to_grant:
        if {"ALL", "GRANT OPTION"} == privileges_to_grant:
            # ALL must be named by itself and cannot be specified along with other privileges
            # The only exception for us is GRANT OPTION but as a WITH clause
            # So handle this case and let the other ones fail
            yield from handle_privileges("GRANT", "TO", {"ALL PRIVILEGES"}, "GRANT OPTION")
        else:
            yield from handle_privileges("GRANT", "TO", privileges_to_grant)

    if privileges_to_grant or privileges_to_revoke:
        if flush:
            yield make_execute_mysql_command(
                "FLUSH PRIVILEGES",
                user=mysql_user,
                password=mysql_password,
                host=mysql_host,
                port=mysql_port,
            )
    else:
        host.noop("mysql privileges are already correct")


_privileges = privileges  # noqa: E305 (for use where kwarg is the same)


@operation(is_idempotent=False)
def dump(
    dest,
    database=None,
    # Details for speaking to MySQL via `mysql` CLI
    mysql_user=None,
    mysql_password=None,
    mysql_host=None,
    mysql_port=None,
):
    """
    Dump a MySQL database into a ``.sql`` file. Requires ``mysqldump``.

    + dest: name of the file to dump the SQL to
    + database: name of the database to dump
    + mysql_*: global module arguments, see above

    **Example:**

    .. code:: python

        mysql.dump(
            name="Dump the pyinfra_stuff database",
            dest="/tmp/pyinfra_stuff.dump",
            database="pyinfra_stuff",
        )
    """

    yield "{0} > {1}".format(
        make_mysql_command(
            executable="mysqldump",
            database=database,
            user=mysql_user,
            password=mysql_password,
            host=mysql_host,
            port=mysql_port,
        ),
        dest,
    )


@operation(is_idempotent=False)
def load(
    src,
    database=None,
    # Details for speaking to MySQL via `mysql` CLI
    mysql_user=None,
    mysql_password=None,
    mysql_host=None,
    mysql_port=None,
):
    """
    Load ``.sql`` file into a database.

    + src: the filename to read from
    + database: name of the database to import into
    + mysql_*: global module arguments, see above

    **Example:**

    .. code:: python

        mysql.load(
            name="Import the pyinfra_stuff dump into pyinfra_stuff_copy",
            src="/tmp/pyinfra_stuff.dump",
            database="pyinfra_stuff_copy",
        )
    """

    commands_bits = [
        make_mysql_command(
            database=database,
            user=mysql_user,
            password=mysql_password,
            host=mysql_host,
            port=mysql_port,
        ),
        "<",
        QuoteString(src),
    ]
    yield StringCommand(*commands_bits)
