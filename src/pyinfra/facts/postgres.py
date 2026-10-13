from __future__ import annotations

import re

from typing_extensions import override

from pyinfra.api import FactBase, HiddenValue, QuoteString, StringCommand
from pyinfra.api.util import try_int

from .util.databases import parse_columns_and_rows

# PostgreSQL configuration parameter names are identifiers: a letter or underscore
# followed by letters, digits or underscores, optionally with a single dotted prefix
# for extension ("custom") parameters such as ``auto_explain.log_min_duration``.
SETTING_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?$")


def quote_sql_literal(value: object) -> str:
    """
    Render a value as a single-quoted PostgreSQL string literal, doubling any
    embedded single quotes to prevent SQL injection.
    """

    return "'" + str(value).replace("'", "''") + "'"


def make_psql_command(
    database: str | None = None,
    user: str | None = None,
    password: str | None = None,
    host: str | None = None,
    port: str | int | None = None,
    executable="psql",
) -> StringCommand:
    target_bits: list[str | StringCommand] = []

    if password:
        target_bits.append(
            StringCommand(
                "PGPASSWORD",
                QuoteString(HiddenValue(password)),
                _separator="=",
            )
        )

    target_bits.append(executable)

    if database:
        target_bits.append(f"-d {database}")

    if user:
        target_bits.append(f"-U {user}")

    if host:
        target_bits.append(f"-h {host}")

    if port:
        target_bits.append(f"-p {port}")

    return StringCommand(*target_bits)


def make_execute_psql_command(command, **psql_kwargs):
    return StringCommand(
        make_psql_command(**psql_kwargs),
        "-Ac",
        QuoteString(command),  # quote this whole item as a single shell argument
    )


class PostgresFactBase(FactBase):
    abstract = True

    psql_command: str

    @override
    def requires_command(self, *args, **kwargs):
        return "psql"

    @override
    def command(
        self,
        psql_user=None,
        psql_password=None,
        psql_host=None,
        psql_port=None,
        psql_database=None,
    ):
        return make_execute_psql_command(
            self.psql_command,
            user=psql_user,
            password=psql_password,
            host=psql_host,
            port=psql_port,
            database=psql_database,
        )


class PostgresRoles(PostgresFactBase):
    """
    Returns a dict of PostgreSQL roles and data:

    .. code:: python

        {
            "pyinfra": {
                "super": true,
                "createrole": false,
                "createdb": false,
                ...
            },
        }
    """

    default = dict
    psql_command = "SELECT * FROM pg_catalog.pg_roles"

    @override
    def process(self, output):
        # Remove the last line of the output (row count)
        output = output[:-1]
        rows = parse_columns_and_rows(
            output,
            "|",
            # Remove the "rol" prefix on column names
            remove_column_prefix="rol",
        )

        users = {}

        for details in rows:
            for key, value in list(details.items()):
                if key in ("oid", "connlimit"):
                    details[key] = try_int(value)

                if key in (
                    "super",
                    "inherit",
                    "createrole",
                    "createdb",
                    "canlogin",
                    "replication",
                    "bypassrls",
                ):
                    details[key] = value == "t"

            users[details.pop("name")] = details

        return users


class PostgresDatabases(PostgresFactBase):
    """
    Returns a dict of PostgreSQL databases and metadata:

    .. code:: python

        {
            "pyinfra_stuff": {
                "encoding": "UTF8",
                "collate": "en_US.UTF-8",
                "ctype": "en_US.UTF-8",
                ...
            },
        }
    """

    default = dict
    psql_command = "SELECT pg_catalog.pg_encoding_to_char(encoding), *, pg_catalog.pg_get_userbyid(datdba) AS owner FROM pg_catalog.pg_database"  # noqa: E501

    @override
    def process(self, output):
        # Remove the last line of the output (row count)
        output = output[:-1]
        rows = parse_columns_and_rows(
            output,
            "|",
            # Remove the "dat" prefix on column names
            remove_column_prefix="dat",
        )

        databases = {}

        for details in rows:
            details["encoding"] = details.pop("pg_encoding_to_char")
            details["owner"] = details.pop("owner")
            for key, value in list(details.items()):
                if key.endswith("id") or key in (
                    "dba",
                    "tablespace",
                    "connlimit",
                ):
                    details[key] = try_int(value)

                if key in ("istemplate", "allowconn"):
                    details[key] = value == "t"

            databases[details.pop("name")] = details

        return databases


def _process_settings_row(row: dict[str, str | None]) -> dict[str, str | None]:
    return {
        "value": row.get("setting"),
        "unit": row.get("unit"),
        "source": row.get("source"),
        "context": row.get("context"),
    }


class PostgresConfiguration(PostgresFactBase):
    """
    Returns a dict of all PostgreSQL run-time configuration settings, as reported
    by ``pg_settings``:

    .. code:: python

        {
            "shared_buffers": {
                "value": "16384",
                "unit": "8kB",
                "source": "configuration file",
                "context": "postmaster",
            },
            ...
        }

    The ``value`` is the *running* value (``pg_settings.setting``), ``source`` is
    where it came from and ``context`` says how a change takes effect (eg
    ``postmaster`` needs a restart, ``sighup`` needs a reload).
    """

    default = dict
    psql_command = "SELECT name, setting, unit, source, context FROM pg_settings ORDER BY name"

    @override
    def process(self, output: list[str]) -> dict[str, dict[str, str | None]]:
        # Remove the last line of the output (row count)
        output = output[:-1]
        rows = parse_columns_and_rows(output, "|")
        return {row.pop("name"): _process_settings_row(row) for row in rows}


class PostgresSetting(PostgresFactBase):
    """
    Returns a single PostgreSQL configuration setting as reported by
    ``pg_settings``, or ``None`` when there is no such setting:

    .. code:: python

        {
            "value": "4096",
            "unit": "kB",
            "source": "default",
            "context": "user",
        }
    """

    @override
    def command(  # type: ignore[override]
        self,
        setting: str,
        psql_user: str | None = None,
        psql_password: str | None = None,
        psql_host: str | None = None,
        psql_port: int | None = None,
        psql_database: str | None = None,
    ) -> StringCommand:
        sql = (
            "SELECT name, setting, unit, source, context FROM pg_settings WHERE name = "
            + quote_sql_literal(setting)
        )
        return make_execute_psql_command(
            sql,
            user=psql_user,
            password=psql_password,
            host=psql_host,
            port=psql_port,
            database=psql_database,
        )

    @override
    def process(self, output: list[str]) -> dict[str, str | None] | None:
        # Remove the last line of the output (row count)
        output = output[:-1]
        rows = parse_columns_and_rows(output, "|")
        if not rows:
            return None
        row = rows[0]
        row.pop("name")
        return _process_settings_row(row)
