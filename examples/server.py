from pyinfra import host
from pyinfra.modules import apt, server, yum

SUDO = True

if host.fact.linux_name in ['CentOS', 'RedHat']:
    yum.packages(
        {'Install some packages'},
        ['cronie'],
        update=True,
    )

if host.fact.linux_name in ['Ubuntu']:
    apt.packages(
        {'Install some packages'},
        ['cron'],
        update=True,
    )

# simple example for a crontab
server.crontab(
    {'Backup /etc weekly'},
    '/bin/tar cf /tmp/etc_bup.tar /etc',
    name='backup_etc',
    day_of_week=0,
    hour=1,
    minute=0,
)

server.group(
    {'Create docker group'},
    'docker',
)

# if we are not running inside a docker container
if not host.fact.file('/.dockerenv'):

    # Cannot change hostname if running in a docker container
    server.hostname(
        {'Set the hostname'},
        'server1.example.com',
    )

    # Cannot change value on read-only filesystem
    # use "/sbin/sysctl -a | grep file-max" to check value
    server.sysctl(
        {'Change the fs.file-max value'},
        'fs.file-max',
        '100000',
        persist=True,
    )

    if host.fact.linux_name in ['CentOS', 'RedHat']:
        server.modprobe(
            {'Silly example for modprobe'},
            'floppy',
        )

server.user(
    {'Ensure user is removed'},
    'kevin',
    present=False,
)

# multiple users
for user in ['kevin', 'bob']:
    server.user(
        {'Ensure user {} is removed'.format(user)},
        user,
        present=False,
    )

server.group(
    {'Create uberadmin group'},
    'uberadmin',
)

# multiple groups
for group in ['wheel', 'lusers']:
    server.group(
        {'Create the group {}'.format(group)},
        group,
    )

# To see output need to run pyinfra with '-v'
server.script(
    {'Hello'},
    'files/hello.bash',
)

# To see output need to run pyinfra with '-v'
server.shell(
    {'Say Hello'},
    'echo Hello',
)
