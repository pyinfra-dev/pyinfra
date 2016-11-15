# pyinfra
# File: pyinfra/modules/postgresql.py
# Desc: manage PostgreSQL databases

'''
The PostgreSQL modules manage PostgreSQL databases
'''

from pyinfra.api import operation


@operation
def user(state, host, username, present=True, superuser=False):
    '''
    Manage PostgreSQL users.

    + username: username in the database
    + superuser: superuser priviledges
    + present: whether the user should be present or absent
    '''
    user = host.fact.postgresql_users.get(username)

    if present:
        if user:
            # Todo: handle user with new permissions
            return
        else:
            options = []
            if superuser:
                options.append('--superuser')

            options_str = ' '.join(options)
            yield 'su postgres -c "createuser {} {}"' \
                  .format(options_str, username)
    elif user:
        raise NotImplemented("PostgreSQL users removal is not supported")


@operation
def database(state, host, name, user='postgres'):
    '''
    Manage PostgreSQL databases.

    + name: name of the database
    + user: user to run the query, the user running pyinfra if None
    + present: whether the user should be present or absent
    '''
    # Avoid double quotes as some will be added around it if user is present
    command = 'createdb {}'.format(name)

    if user:
        yield 'su {} -c "{}"'.format(user, command)
    else:
        yield command
