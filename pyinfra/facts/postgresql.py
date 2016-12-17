# pyinfra
# File: pyinfra/facts/postgresql.py
# Desc: PostgreSQL facts

import json

from pyinfra.api import FactBase


class PostgresqlUsers(FactBase):
    '''
    Returns a list of PostgreSQL users.

    This fact lists all users registered in PostgreSQL, as well as their basic
    configuration and permissions.

    See PostgreSQL documentation for more information on the fields returned:
    https://www.postgresql.org/docs/current/static/view-pg-user.html
    '''

    # This command assumes that PostgreSQL is configured to run as user
    # 'postgres'. This is the case on Ubuntu and probably other common
    # distributions but might not always be true.
    command = 'sudo -u postgres -- psql postgres -tAc "SELECT * FROM pg_user;"'

    def process(self, output):
        users = {}
        for line in output:
            usename, usesysid, usecreatedb, usesuper, userepl, usebypassrls, \
                passwd, valuntil, useconfig = line.split('|')

            # Transform boolean values
            users[usename] = {
                'usesysid': usesysid == 't',
                'usecreatedb': usecreatedb == 't',
                'usesuper': usesuper == 't',
                'userepl': userepl == 't',
                'usebypassrls': usebypassrls == 't',
                'valuntil': valuntil,
                'useconfig': valuntil,
            }
        return users
