"""
The PostgreSQL modules manage PostgreSQL databases, users and privileges.

Requires the ``psql`` CLI executable on the target host(s).

All operations in this module take four optional arguments:
    + ``psql_user``: the username to connect to postgresql to
    + ``psql_password``: the password for the connecting user
    + ``psql_host``: the hostname of the server to connect to
    + ``psql_port``: the port of the server to connect to
    + ``psql_database``: the database on the server to connect to

See example/postgresql.py for detailed example

"""

from __future__ import annotations

import re

from pyinfra import host
from pyinfra.api import HiddenValue, OperationError, QuoteString, StringCommand, operation
from pyinfra.facts.postgres import (
    SETTING_NAME_RE,
    PostgresConfiguration,
    PostgresDatabases,
    PostgresRoles,
    make_execute_psql_command,
    make_psql_command,
    quote_sql_literal,
)


@operation(is_idempotent=False)
def sql(
    sql: str,
    # Details for speaking to PostgreSQL via `psql` CLI
    psql_user: str | None = None,
    psql_password: str | None = None,
    psql_host: str | None = None,
    psql_port: int | None = None,
    psql_database: str | None = None,
):
    """
    Execute arbitrary SQL against PostgreSQL.

    + sql: SQL command(s) to execute
    + psql_*: global module arguments, see above
    """

    yield make_execute_psql_command(
        sql,
        user=psql_user,
        password=psql_password,
        host=psql_host,
        port=psql_port,
        database=psql_database,
    )


@operation(
    idempotent_notice=(
        "This operation will always execute commands when a password is provided, "
        "as pyinfra cannot reliably validate the current password."
    ),
)
def role(
    role: str,
    present: bool = True,
    password: str | None = None,
    login: bool = True,
    superuser: bool = False,
    inherit: bool = False,
    createdb: bool = False,
    createrole: bool = False,
    replication: bool = False,
    connection_limit: int | None = None,
    # Details for speaking to PostgreSQL via `psql` CLI
    psql_user: str | None = None,
    psql_password: str | None = None,
    psql_host: str | None = None,
    psql_port: int | None = None,
    psql_database: str | None = None,
):
    """
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
    + psql_*: global module arguments, see above

    Updates:
        pyinfra will not attempt to change existing roles - it will either
        create or drop roles, but not alter them (if the role exists this
        operation will make no changes).

    **Example:**

    .. code:: python

        from pyinfra.operations import postgresql
        postgresql.role(
            name="Create the pyinfra PostgreSQL role",
            role="pyinfra",
            password="somepassword",
            superuser=True,
            login=True,
            _sudo_user="postgres",
        )

    """

    roles = host.get_fact(
        PostgresRoles,
        psql_user=psql_user,
        psql_password=psql_password,
        psql_host=psql_host,
        psql_port=psql_port,
        psql_database=psql_database,
    )

    is_present = role in roles

    # User not wanted?
    if not present:
        if is_present:
            yield make_execute_psql_command(
                f'DROP ROLE "{role}"',
                user=psql_user,
                password=psql_password,
                host=psql_host,
                port=psql_port,
                database=psql_database,
            )
        else:
            host.noop(f"postgresql role {role} does not exist")
        return

    # If we want the user and they don't exist
    if not is_present:
        sql_bits: list[str | StringCommand] = [f'CREATE ROLE "{role}"']

        for key, value in (
            ("LOGIN", login),
            ("SUPERUSER", superuser),
            ("INHERIT", inherit),
            ("CREATEDB", createdb),
            ("CREATEROLE", createrole),
            ("REPLICATION", replication),
        ):
            if value:
                sql_bits.append(key)

        if connection_limit:
            sql_bits.append(f"CONNECTION LIMIT {connection_limit}")

        if password:
            sql_bits.append(
                StringCommand(
                    "PASSWORD", StringCommand("'", HiddenValue(password), "'", _separator="")
                )
            )

        yield make_execute_psql_command(
            StringCommand(*sql_bits),
            user=psql_user,
            password=psql_password,
            host=psql_host,
            port=psql_port,
            database=psql_database,
        )
    else:
        # Check if any attributes need updating
        current_role = roles[role]
        should_execute = False
        sql_bits = [f'ALTER ROLE "{role}"']
        if login and "login" in current_role and current_role["login"] != login:
            sql_bits.append("LOGIN")
            should_execute = True
        if superuser and "superuser" in current_role and current_role["superuser"] != superuser:
            sql_bits.append("SUPERUSER")
            should_execute = True
        if inherit and "inherit" in current_role and current_role["inherit"] != inherit:
            sql_bits.append("INHERIT")
            should_execute = True
        if createdb and "createdb" in current_role and current_role["createdb"] != createdb:
            sql_bits.append("CREATEDB")
            should_execute = True
        if createrole and "createrole" in current_role and current_role["createrole"] != createrole:
            sql_bits.append("CREATEROLE")
            should_execute = True
        if (
            connection_limit
            and "connection_limit" in current_role
            and roles[role]["connection_limit"] != connection_limit
        ):
            sql_bits.append(f"CONNECTION LIMIT {connection_limit}")
            should_execute = True
        if password:
            sql_bits.append(
                StringCommand(
                    "PASSWORD", StringCommand("'", HiddenValue(password), "'", _separator="")
                )
            )
            should_execute = True

        if should_execute:
            yield make_execute_psql_command(
                StringCommand(*sql_bits),
                user=psql_user,
                password=psql_password,
                host=psql_host,
                port=psql_port,
                database=psql_database,
            )
        else:
            host.noop(f"postgresql role {role} exists and does not need updates")


@operation()
def database(
    database: str,
    present=True,
    owner: str | None = None,
    template: str | None = None,
    encoding: str | None = None,
    lc_collate: str | None = None,
    lc_ctype: str | None = None,
    tablespace: str | None = None,
    connection_limit: int | None = None,
    # Details for speaking to PostgreSQL via `psql` CLI
    psql_user: str | None = None,
    psql_password: str | None = None,
    psql_host: str | None = None,
    psql_port: int | None = None,
    psql_database: str | None = None,
):
    """
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
    + psql_*: global module arguments, see above

    Updates:
        pyinfra will change existing databases - but some parameters are not
        changeable (template, encoding, lc_collate and lc_ctype).

    **Example:**

    .. code:: python

        postgresql.database(
            name="Create the pyinfra_stuff database",
            database="pyinfra_stuff",
            owner="pyinfra",
            encoding="UTF8",
            _sudo_user="postgres",
        )

    """

    current_databases = host.get_fact(
        PostgresDatabases,
        psql_user=psql_user,
        psql_password=psql_password,
        psql_host=psql_host,
        psql_port=psql_port,
        psql_database=psql_database,
    )

    is_present = database in current_databases

    if not present:
        if is_present:
            yield make_execute_psql_command(
                f'DROP DATABASE "{database}"',
                user=psql_user,
                password=psql_password,
                host=psql_host,
                port=psql_port,
                database=psql_database,
            )
        else:
            host.noop(f"postgresql database {database} does not exist")
        return

    # We want the database but it doesn't exist
    if present and not is_present:
        sql_bits = [f'CREATE DATABASE "{database}"']

        for key, value in (
            ("OWNER", f'"{owner}"' if owner else owner),
            ("TEMPLATE", template),
            ("ENCODING", encoding),
            ("LC_COLLATE", f"'{lc_collate}'" if lc_collate else lc_collate),
            ("LC_CTYPE", f"'{lc_ctype}'" if lc_ctype else lc_ctype),
            ("TABLESPACE", tablespace),
            ("CONNECTION LIMIT", connection_limit),
        ):
            if value:
                sql_bits.append(f"{key} {value}")

        yield make_execute_psql_command(
            StringCommand(*sql_bits),
            user=psql_user,
            password=psql_password,
            host=psql_host,
            port=psql_port,
            database=psql_database,
        )
    else:
        current_db = current_databases[database]

        for key, value, current_value in (
            ("TEMPLATE", template, current_db.get("istemplate")),
            ("ENCODING", encoding, current_db.get("encoding")),
            ("LC_COLLATE", lc_collate, None),
            ("LC_CTYPE", lc_ctype, None),
        ):
            if value and (current_value is None or current_value != value):
                host.noop(f"postgresql database {database} already exists, skipping {key}")

        sql_bits = []

        if owner and "owner" in current_db and current_db["owner"] != owner:
            sql_bits.append(f'ALTER DATABASE "{database}" OWNER TO "{owner}";')

        if tablespace and "tablespace" in current_db and current_db["tablespace"] != tablespace:
            sql_bits.append(f'ALTER DATABASE "{database}" SET TABLESPACE "{tablespace}";')

        if (
            connection_limit
            and "connlimit" in current_db
            and current_db["connlimit"] != connection_limit
        ):
            sql_bits.append(f'ALTER DATABASE "{database}" CONNECTION LIMIT {connection_limit};')

        if len(sql_bits) > 0:
            yield make_execute_psql_command(
                StringCommand(*sql_bits),
                user=psql_user,
                password=psql_password,
                host=psql_host,
                port=psql_port,
                database=psql_database,
            )
        else:
            host.noop(f"postgresql database {database} already exists with the same parameters")


@operation(is_idempotent=False)
def dump(
    dest: str,
    # Details for speaking to PostgreSQL via `psql` CLI
    psql_user: str | None = None,
    psql_password: str | None = None,
    psql_host: str | None = None,
    psql_port: int | None = None,
    psql_database: str | None = None,
):
    """
    Dump a PostgreSQL database into a ``.sql`` file. Requires ``pg_dump``.

    + dest: name of the file to dump the SQL to
    + psql_*: global module arguments, see above

    **Example:**

    .. code:: python

        postgresql.dump(
            name="Dump the pyinfra_stuff database",
            dest="/tmp/pyinfra_stuff.dump",
            sudo_user="postgres",
        )

    """

    yield StringCommand(
        make_psql_command(
            executable="pg_dump",
            user=psql_user,
            password=psql_password,
            host=psql_host,
            port=psql_port,
            database=psql_database,
        ),
        ">",
        QuoteString(dest),
    )


@operation(is_idempotent=False)
def load(
    src: str,
    # Details for speaking to PostgreSQL via `psql` CLI
    psql_user: str | None = None,
    psql_password: str | None = None,
    psql_host: str | None = None,
    psql_port: int | None = None,
    psql_database: str | None = None,
):
    """
    Load ``.sql`` file into a database.

    + src: the filename to read from
    + psql_*: global module arguments, see above

    **Example:**

    .. code:: python

        postgresql.load(
            name="Import the pyinfra_stuff dump into pyinfra_stuff_copy",
            src="/tmp/pyinfra_stuff.dump",
            sudo_user="postgres",
        )

    """

    yield StringCommand(
        make_psql_command(
            user=psql_user,
            password=psql_password,
            host=psql_host,
            port=psql_port,
            database=psql_database,
        ),
        "<",
        QuoteString(src),
    )


# Multipliers used to normalise PostgreSQL memory/time settings so an operation
# value such as "128MB" can be compared against the raw value + unit pg_settings
# reports (eg setting="16384", unit="8kB"). Memory is reduced to bytes and time
# to microseconds.
_MEMORY_UNITS = {"b": 1, "kb": 1024, "mb": 1024**2, "gb": 1024**3, "tb": 1024**4}
_TIME_UNITS = {
    "us": 1,
    "ms": 1000,
    "s": 1_000_000,
    "min": 60_000_000,
    "h": 3_600_000_000,
    "d": 86_400_000_000,
}
_UNIT_SCALES = {**_MEMORY_UNITS, **_TIME_UNITS}

_TRUE_VALUES = {"on", "true", "yes", "1"}
_FALSE_VALUES = {"off", "false", "no", "0"}

# A bare quantity ("128", "2.5") with an optional unit suffix ("128MB", "30s").
_QUANTITY_RE = re.compile(r"^(-?\d+(?:\.\d+)?)\s*([a-zA-Z]*)$")
# A pg_settings unit, optionally prefixed with a block multiplier ("8kB", "kB").
_UNIT_RE = re.compile(r"^(\d*)\s*([a-zA-Z]+)$")


def _to_bool(value: str) -> bool | None:
    lowered = value.strip().lower()
    if lowered in _TRUE_VALUES:
        return True
    if lowered in _FALSE_VALUES:
        return False
    return None


def _to_number(value: str) -> int | float | None:
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return None


def _quantity_match(desired: str, current: str, unit: str) -> bool:
    unit_match = _UNIT_RE.match(unit)
    if unit_match is None:
        return False
    unit_multiplier = int(unit_match.group(1)) if unit_match.group(1) else 1
    unit_scale = _UNIT_SCALES.get(unit_match.group(2).lower())
    if unit_scale is None:
        return False

    current_number = _to_number(current)
    if current_number is None:
        return False
    current_base = current_number * unit_multiplier * unit_scale

    desired_match = _QUANTITY_RE.match(desired)
    if desired_match is None:
        return False
    desired_number = _to_number(desired_match.group(1))
    if desired_number is None:
        return False
    suffix = desired_match.group(2)
    if suffix:
        suffix_scale = _UNIT_SCALES.get(suffix.lower())
        if suffix_scale is None:
            return False
        desired_base = desired_number * suffix_scale
    else:
        # A bare number is interpreted as a count in the setting's own unit.
        desired_base = desired_number * unit_multiplier * unit_scale

    return current_base == desired_base


def _values_match(desired: object, current_value: str | None, unit: str | None) -> bool:
    if current_value is None:
        return False

    desired_str = str(desired).strip()
    current_str = current_value.strip()
    if desired_str == current_str:
        return True

    if unit:
        return _quantity_match(desired_str, current_str, unit)

    desired_bool = _to_bool(desired_str)
    current_bool = _to_bool(current_str)
    if desired_bool is not None and current_bool is not None:
        return desired_bool == current_bool

    desired_number = _to_number(desired_str)
    current_number = _to_number(current_str)
    if desired_number is not None and current_number is not None:
        return desired_number == current_number

    return desired_str.lower() == current_str.lower()


@operation(
    idempotent_notice=(
        "ALTER SYSTEM writes to postgresql.auto.conf; until the server reloads or "
        "restarts, pg_settings still reports the old value, so this operation will "
        "re-issue the change on each run until it is applied."
    ),
)
def configuration(
    setting: str,
    value: str | int | bool | None = None,
    present: bool = True,
    # Details for speaking to PostgreSQL via `psql` CLI
    psql_user: str | None = None,
    psql_password: str | None = None,
    psql_host: str | None = None,
    psql_port: int | None = None,
    psql_database: str | None = None,
):
    """
    Set or reset a PostgreSQL server configuration parameter with ``ALTER SYSTEM``.

    + setting: name of the configuration parameter (eg ``work_mem``)
    + value: desired value, required when ``present`` is ``True``
    + present: ``True`` to set ``value``, ``False`` to reset the setting to its
      default with ``ALTER SYSTEM RESET``
    + psql_*: global module arguments, see above

    Reload/restart:
        ``ALTER SYSTEM`` only writes ``postgresql.auto.conf``. Changes take effect
        after the server reloads (``postgres.sql("SELECT pg_reload_conf()")``) or,
        for settings whose ``context`` is ``postmaster``, after a full restart.
        This operation never reloads or restarts for you, so it compares against
        the *running* value and becomes a no-op once the change is live.

    **Example:**

    .. code:: python

        postgres.configuration(
            name="Increase work_mem",
            setting="work_mem",
            value="8MB",
            _sudo_user="postgres",
        )
    """

    if not SETTING_NAME_RE.match(setting):
        raise OperationError(f"invalid PostgreSQL setting name: {setting}")

    if present and value is None:
        raise OperationError("`value` is required when `present` is True")

    current = host.get_fact(
        PostgresConfiguration,
        psql_user=psql_user,
        psql_password=psql_password,
        psql_host=psql_host,
        psql_port=psql_port,
        psql_database=psql_database,
    ).get(setting)

    if not present:
        if current is None:
            host.noop(f"postgresql setting {setting} is not set")
            return
        if current.get("source") == "default":
            host.noop(f"postgresql setting {setting} is already at its default")
            return
        yield make_execute_psql_command(
            f"ALTER SYSTEM RESET {setting}",
            user=psql_user,
            password=psql_password,
            host=psql_host,
            port=psql_port,
            database=psql_database,
        )
        return

    if current is not None and _values_match(value, current.get("value"), current.get("unit")):
        host.noop(f"postgresql setting {setting} is already set to {value}")
        return

    yield make_execute_psql_command(
        f"ALTER SYSTEM SET {setting} = {quote_sql_literal(value)}",
        user=psql_user,
        password=psql_password,
        host=psql_host,
        port=psql_port,
        database=psql_database,
    )
