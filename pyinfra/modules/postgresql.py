# pyinfra
# File: pyinfra/modules/postgresql.py
# Desc: manage PostgreSQL databases

'''
The PostgreSQL modules manage PostgreSQL databases
'''

from pyinfra.api import operation


@operation
def user(state, host, username, present=True,
         createdb=None, createrole=None, superuser=None, replication=None,
         ):
    '''
    Manage PostgreSQL users.

    + username: username in the database
    + present: whether the user should be present or absent
    + createdb: user is allowed to create databases
    + createrole: user is allowed to create new roles
    + superuser: user will be a superuser
    + replication: user has the replication privilege
    '''
    user = host.fact.postgresql_users.get(username)

    if present:
        if user:
            # Todo: handle user with new permissions
            return
        else:
            options = []

            # Explicitely setting
            for arg in 'createdb', 'createrole', 'superuser', 'replication':
                if locals()[arg] is True:
                    options.append('--{}'.format(arg))
                elif locals()[arg] is False:
                    options.append('--no-{}'.format(arg))

            options_str = ' '.join(options)
            yield 'createuser {} {}' \
                  .format(options_str, username)
    elif user:
        raise NotImplemented("PostgreSQL users removal is not supported")


@operation
def database(state, host, name):
    '''
    Manage PostgreSQL databases.

    + name: name of the database
    + user: user to run the query, the user running pyinfra if None
    + present: whether the user should be present or absent
    '''
    # Avoid double quotes as some will be added around it if user is present
    yield 'createdb {}'.format(name)
