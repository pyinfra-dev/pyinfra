from pyinfra import host, state
from pyinfra.facts.server import LinuxName
from pyinfra.operations import apt, files, postgresql, python

SUDO = True


if host.get_fact(LinuxName) != 'Ubuntu':
    # Raises an exception mid-deploy
    python.raise_exception(
        name='Ensure we are Ubuntu',
        exception=NotImplementedError,
        args=('`postgresql.py` only works on Ubuntu',),
    )


apt.packages(
    name='Install postgresql server & client',
    packages=['postgresql'],
    update=True,
    cache_time=3600,
)


# Setup a PostgreSQL role & database
#

postgresql.role(
    name='Create the pyinfra PostgreSQL role',
    role='pyinfra',
    password='somepassword',
    superuser=True,
    login=True,
    sudo_user='postgres',
)

postgresql.database(
    name='Create the pyinfra_stuff database',
    database='pyinfra_stuff',
    owner='pyinfra',
    encoding='UTF8',
    sudo_user='postgres',
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

postgresql.load(
    name='Import the uploaded a_db.sql file',
    src=temp_filename,
    database='pyinfra_stuff',
    sudo_user='postgres',
)


# Now duplicate the pyinfra_stuff database -> pyinfra_stuff_copy
#

postgresql.database(
    name='Create the pyinfra_stuff_copy database',
    database='pyinfra_stuff_copy',
    sudo_user='postgres',
)

dump_filename = state.get_temp_filename('psql_dump')

postgresql.dump(
    name='Dump the pyinfra_stuff database',
    dest=dump_filename,
    database='pyinfra_stuff',
    sudo_user='postgres',
)

postgresql.load(
    name='Import the pyinfra_stuff dump into pyinfra_stuff_copy',
    src=dump_filename,
    database='pyinfra_stuff_copy',
    sudo_user='postgres',
)
