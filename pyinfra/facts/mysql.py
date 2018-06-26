# pyinfra
# File: pyinfra/facts/mysql.py
# Desc: facts for the MySQL server

import re

from collections import defaultdict

import six

from pyinfra.api import FactBase


def make_mysql_command(
    database=None,
    user=None,
    password=None,
    host=None,
    port=None,
    executable='mysql',
):
    target_bits = [executable]

    if database:
        target_bits.append(database)

    if user:
        # Quote the username as in may contain special characters
        target_bits.append('-u"{0}"'.format(user))

    if password:
        # Quote the password as it may contain special characters
        target_bits.append('-p"{0}"'.format(password))

    if host:
        target_bits.append('-h{0}'.format(host))

    if port:
        target_bits.append('-P{0}'.format(port))

    return ' '.join(target_bits)


def make_execute_mysql_command(command, **mysql_kwargs):
    command = command.replace('"', '\\"')
    mysql_command = make_mysql_command(**mysql_kwargs)
    return 'echo "{0};" | {1}'.format(command, mysql_command)


class MysqlFactBase(FactBase):
    abstract = True

    def command(
        self,
        # Details for speaking to MySQL via `mysql` CLI via `mysql` CLI
        mysql_user=None, mysql_password=None,
        mysql_host=None, mysql_port=None,
    ):
        return make_execute_mysql_command(
            self.mysql_command,
            user=mysql_user,
            password=mysql_password,
            host=mysql_host,
            port=mysql_port,
        )


class MysqlDatabases(MysqlFactBase):
    '''
    Returns a list of existing MySQL databases.
    '''

    default = list
    mysql_command = 'SHOW DATABASES'

    def process(self, output):
        return output[1:]


class MysqlUsers(MysqlFactBase):
    '''
    Returns a dict of MySQL user@host's and their associated data:

    .. code:: python

        'user@host': {
            'permissions': ['Alter', 'Grant'],
            'max_connections': 5,
            ...
        },
        ...
    '''

    default = dict
    mysql_command = 'SELECT * FROM mysql.user'

    @staticmethod
    def process(output):
        users = {}

        # Get the titles
        titles = output[0]
        titles = titles.split('\t')

        for row in output[1:]:
            bits = row.split('\t')
            details = {}

            # Attach user columns by title
            for i, bit in enumerate(bits):
                if not bit:
                    continue

                details[titles[i]] = bit

            if 'Host' in details and 'User' in details:
                # Pop off any true permission values
                permissions = [
                    key.replace('_priv', '')
                    for key in list(six.iterkeys(details))
                    if key.endswith('_priv') and details.pop(key) == 'Y'
                ]
                details['permissions'] = permissions

                # Attach the user in the format user@host
                users['{0}@{1}'.format(
                    details.pop('User'), details.pop('Host'),
                )] = details

        return users


MYSQL_GRANT_REGEX = re.compile(
    r"^GRANT ([A-Z,\s]+) ON (\*|`[a-z_\\]+`\.\*|'[a-z_]+') TO '[a-z_]+'@'[a-z]+'(.*)",
)


class MysqlUserGrants(MysqlFactBase):
    default = dict

    def command(
        self, user,
        hostname='localhost',
        # Details for speaking to MySQL via `mysql` CLI via `mysql` CLI
        mysql_user=None, mysql_password=None,
        mysql_host=None, mysql_port=None,
    ):
        self.mysql_command = 'SHOW GRANTS FOR "{0}"@"{1}"'.format(user, hostname)

        return super(MysqlUserGrants, self).command(
            mysql_user, mysql_password,
            mysql_host, mysql_port,
        )

    @staticmethod
    def process(output):
        database_table_permissions = defaultdict(lambda: {
            'permissions': set(),
            'with_grant_option': False,
        })

        for line in output:
            matches = re.match(MYSQL_GRANT_REGEX, line)
            if not matches:
                continue

            permissions, database_table, extras = matches.groups()

            # MySQL outputs this pre-escaped
            database_table = database_table.replace('\\\\', '\\')

            for permission in permissions.split(','):
                permission = permission.strip()
                database_table_permissions[database_table]['permissions'].add(permission)

            if 'WITH GRANT OPTION' in extras:
                database_table_permissions[database_table]['with_grant_option'] = True

        return database_table_permissions
