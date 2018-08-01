from pyinfra import host
from pyinfra.modules import apt, mysql, python

SUDO = True


distro = host.fact.linux_distribution['name']


if distro != 'Debian':
    # Raises an exception mid-deploy
    python.raise_exception(
        {'Ensure we are Debian'},
        NotImplementedError,
        '`deploy_mysql.py` only works on Debian',
    )


apt.packages(
    {'Install mysql server & client'},
    ['mysql-server'],
    update=True,
    cache_time=3600,
)


mysql.user(
    {'Setup the pyinfra@localhost MySQL user'},
    'pyinfra',
)

mysql.database(
    {'Setup the pyinfra_stuff database'},
    'pyinfra_stuff',
    user='pyinfra',
)
