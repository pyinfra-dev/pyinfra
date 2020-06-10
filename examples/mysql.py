from pyinfra import host, state
from pyinfra.operations import apt, files, mysql, python

SUDO = True


if host.fact.linux_name != 'Debian':
    # Raises an exception mid-deploy
    python.raise_exception(
        {'Ensure we are Debian'},
        NotImplementedError,
        '`mysql.py` only works on Debian',
    )


apt.packages(
    {'Install mysql server & client'},
    ['mysql-server'],
    update=True,
    cache_time=3600,
)


# Setup a MySQL role & database
#

mysql.user(
    {'Create the pyinfra@localhost MySQL user'},
    'pyinfra',
    password='somepassword',
)

mysql.database(
    {'Create the pyinfra_stuff database'},
    'pyinfra_stuff',
    user='pyinfra',
    user_privileges=['SELECT', 'INSERT'],
    charset='utf8',
)


# Upload & import a SQL file into the pyinfra_stuff database
#

filename = 'files/a_db.sql'
temp_filename = state.get_temp_filename(filename)

files.put(
    {'Upload the a_db.sql file'},
    filename, temp_filename,
)

mysql.load(
    {'Import the a_db.sql file'},
    temp_filename,
    database='pyinfra_stuff',
)


# Now duplicate the pyinfra_stuff database -> pyinfra_stuff_copy
#

mysql.database(
    {'Create the pyinfra_stuff_copy database'},
    'pyinfra_stuff_copy',
    charset='utf8',
)

dump_filename = state.get_temp_filename('mysql_dump')

mysql.dump(
    {'Dump the pyinfra_stuff database'},
    dump_filename,
    database='pyinfra_stuff',
)

mysql.load(
    {'Import the pyinfra_stuff dump into pyinfra_stuff_copy'},
    dump_filename,
    database='pyinfra_stuff_copy',
)
