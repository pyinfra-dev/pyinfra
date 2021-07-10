from pyinfra import host, state
from pyinfra.facts.server import LinuxName
from pyinfra.operations import apt, files, mysql, python

SUDO = True


if host.get_fact(LinuxName) != 'Debian':
    # Raises an exception mid-deploy
    python.raise_exception(
        name='Ensure we are Debian',
        exception=NotImplementedError,
        args=('`mysql.py` only works on Debian',),
    )


apt.packages(
    name='Install mysql server & client',
    packages=['mysql-server'],
    update=True,
    cache_time=3600,
)


# Setup a MySQL role & database
#

mysql.user(
    name='Create the pyinfra@localhost MySQL user',
    user='pyinfra',
    password='somepassword',
)

mysql.database(
    name='Create the pyinfra_stuff database',
    database='pyinfra_stuff',
    user='pyinfra',
    user_privileges=['SELECT', 'INSERT'],
    charset='utf8',
)


# Upload & import a SQL file into the pyinfra_stuff database
#

filename = 'files/a_db.sql'
temp_filename = state.get_temp_filename(filename)

files.put(
    name='Upload the a_db.sql file',
    src=filename,
    dest=temp_filename,
)

mysql.load(
    name='Import the a_db.sql file',
    src=temp_filename,
    database='pyinfra_stuff',
)


# Now duplicate the pyinfra_stuff database -> pyinfra_stuff_copy
#

mysql.database(
    name='Create the pyinfra_stuff_copy database',
    database='pyinfra_stuff_copy',
    charset='utf8',
)

dump_filename = state.get_temp_filename('mysql_dump')

mysql.dump(
    name='Dump the pyinfra_stuff database',
    dest=dump_filename,
    database='pyinfra_stuff',
)

mysql.load(
    name='Import the pyinfra_stuff dump into pyinfra_stuff_copy',
    src=dump_filename,
    database='pyinfra_stuff_copy',
)
