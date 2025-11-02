from __future__ import annotations

from .postgres import PostgresDatabases, PostgresRoles


class PostgresqlRoles(PostgresRoles):
    deprecated = True


class PostgresqlDatabases(PostgresDatabases):
    deprecated = True
