import re

from collections import defaultdict

from pyinfra.api import FactBase, MaskString, QuoteString, StringCommand
from pyinfra.api.util import try_int

from .util.databases import parse_columns_and_rows


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
        target_bits.append(MaskString('-p"{0}"'.format(password)))

    if host:
        target_bits.append('-h{0}'.format(host))

    if port:
        target_bits.append('-P{0}'.format(port))

    return StringCommand(*target_bits)


def make_execute_mysql_command(command, ignore_errors=False, **mysql_kwargs):
    commands_bits = [
        make_mysql_command(**mysql_kwargs),
        '-Be',
        QuoteString(command),  # quote this whole item as a single shell argument
    ]

    if ignore_errors:
        commands_bits.extend(['||', 'true'])

    return StringCommand(*commands_bits)


class MysqlFactBase(FactBase):
    abstract = True

    requires_command = 'mysql'
    ignore_errors = False

    def command(
        self,
        # Details for speaking to MySQL via `mysql` CLI via `mysql` CLI
        mysql_user=None, mysql_password=None,
        mysql_host=None, mysql_port=None,
    ):
        return make_execute_mysql_command(
            self.mysql_command,
            ignore_errors=self.ignore_errors,
            user=mysql_user,
            password=mysql_password,
            host=mysql_host,
            port=mysql_port,
        )


class MysqlDatabases(MysqlFactBase):
    '''
    Returns a dict of existing MySQL databases and associated data:

    .. code:: python

        {
            'mysql': {
                'character_set': 'latin1',
                'collation_name': 'latin1_swedish_ci'
            },
        }
    '''

    default = dict
    mysql_command = 'SELECT * FROM information_schema.SCHEMATA'

    def process(self, output):
        rows = parse_columns_and_rows(
            output, '\t',
            title_parser=lambda title: title.lower(),
        )

        databases = {}

        for details in rows:
            databases[details.pop('schema_name')] = {
                'character_set': details['default_character_set_name'],
                'collation_name': details['default_collation_name'],
            }

        return databases


class MysqlUsers(MysqlFactBase):
    '''
    Returns a dict of MySQL ``user@host``'s and their associated data:

    .. code:: python

        {
            'user@host': {
                'privileges': ['Alter', 'Grant'],
                'max_connections': 5,
                ...
            },
        }
    '''

    default = dict
    mysql_command = 'SELECT * FROM mysql.user'

    @staticmethod
    def process(output):
        rows = parse_columns_and_rows(output, '\t')

        users = {}

        for details in rows:
            if details.get('Host') is None or details.get('User') is None:
                continue  # pragma: no cover

            privileges = []

            for key, value in list(details.items()):
                if key.endswith('_priv') and details.pop(key) == 'Y':
                    privileges.append(key.replace('_priv', ''))

                if key.startswith('max_'):
                    details[key] = try_int(value)

                if key in ('password_expired', 'is_role'):
                    details[key] = value == 'Y'

            details['privileges'] = sorted(privileges)

            # Attach the user in the format user@host
            users['{0}@{1}'.format(
                details.pop('User'), details.pop('Host'),
            )] = details

        return users


MYSQL_GRANT_REGEX = (
    r"^GRANT ([A-Z,\s]+) ON (\*|`[a-z_\\]+`\.\*|'[a-z_]+') "
    r'TO `[A-Z0-9a-z_\-]+`@`[A-Z0-9a-z_\.\-]+`(.*)'
)


class MysqlUserGrants(MysqlFactBase):
    '''
    Returns a dict of ``<database>`.<table>`` with granted privileges for each:

    .. code:: python

        {
            '`pyinfra_stuff`.*': {
                'privileges': [
                    'SELECT',
                    'INSERT'
                ],
                "with_grant_option": false
            },
        }
    '''

    default = dict
    # Ignore errors as SHOW GRANTS will error if the user does not exist
    ignore_errors = True

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
        database_table_privileges = defaultdict(lambda: {
            'privileges': set(),
            'with_grant_option': False,
        })

        for line in output:
            matches = re.match(MYSQL_GRANT_REGEX, line)
            if not matches:
                continue

            privileges, database_table, extras = matches.groups()

            # MySQL outputs this pre-escaped
            database_table = database_table.replace('\\\\', '\\')

            for privilege in privileges.split(','):
                privilege = privilege.strip()
                database_table_privileges[database_table]['privileges'].add(privilege)

            if 'WITH GRANT OPTION' in extras:
                database_table_privileges[database_table]['with_grant_option'] = True

        return database_table_privileges
