from pyinfra import host, state
from pyinfra.modules import apt, files, postgresql, python

SUDO = True


if host.fact.linux_distribution['name'] != 'Ubuntu':
    # Raises an exception mid-deploy
    python.raise_exception(
        {'Ensure we are Ubuntu'},
        NotImplementedError,
        '`postgresql.py` only works on Ubuntu',
    )


apt.packages(
    {'Install postgresql server & client'},
    ['postgresql'],
    update=True,
    cache_time=3600,
)


# Setup a PostgreSQL role & database
#

postgresql.role(
    {'Create the pyinfra PostgreSQL role'},
    'pyinfra',
    password='somepassword',
    superuser=True,
    login=True,
    sudo_user='postgres',
)

postgresql.database(
    {'Create the pyinfra_stuff database'},
    'pyinfra_stuff',
    owner='pyinfra',
    encoding='UTF8',
    sudo_user='postgres',
)


# Upload & import a SQL file into the pyinfra_stuff database
#

filename = 'files/a_db.sql'
temp_filename = state.get_temp_filename(filename)

files.put(
    {'Upload the a_db.sql file'},
    filename, temp_filename,
)

postgresql.load(
    {'Import the uploaded a_db.sql file'},
    temp_filename,
    database='pyinfra_stuff',
    sudo_user='postgres',
)


# Now duplicate the pyinfra_stuff database -> pyinfra_stuff_copy
#

postgresql.database(
    {'Create the pyinfra_stuff_copy database'},
    'pyinfra_stuff_copy',
    sudo_user='postgres',
)

dump_filename = state.get_temp_filename('psql_dump')

postgresql.dump(
    {'Dump the pyinfra_stuff database'},
    dump_filename,
    database='pyinfra_stuff',
    sudo_user='postgres',
)

postgresql.load(
    {'Import the pyinfra_stuff dump into pyinfra_stuff_copy'},
    dump_filename,
    database='pyinfra_stuff_copy',
    sudo_user='postgres',
)
