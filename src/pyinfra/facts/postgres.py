from __future__ import annotations

from typing_extensions import override

from pyinfra.api import FactBase, MaskString, QuoteString, StringCommand
from pyinfra.api.util import try_int

from .util.databases import parse_columns_and_rows


def make_psql_command(
    database: str | None = None,
    user: str | None = None,
    password: str | None = None,
    host: str | None = None,
    port: str | int | None = None,
    executable="psql",
) -> StringCommand:
    target_bits: list[str] = []

    if password:
        target_bits.append(MaskString('PGPASSWORD="{0}"'.format(password)))

    target_bits.append(executable)

    if database:
        target_bits.append("-d {0}".format(database))

    if user:
        target_bits.append("-U {0}".format(user))

    if host:
        target_bits.append("-h {0}".format(host))

    if port:
        target_bits.append("-p {0}".format(port))

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
