from pyinfra import host
from pyinfra.facts.files import File
from pyinfra.facts.server import LinuxName
from pyinfra.operations import apt, server, yum

SUDO = True

if host.get_fact(LinuxName) in ['CentOS', 'RedHat']:
    yum.packages(
        name='Install some packages',
        packages=['cronie'],
        update=True,
    )

if host.get_fact(LinuxName) in ['Ubuntu']:
    apt.packages(
        name='Install some packages',
        packages=['cron'],
        update=True,
    )

# simple example for a crontab
server.crontab(
    name='Backup /etc weekly',
    command='/bin/tar cf /tmp/etc_bup.tar /etc',
    cron_name='backup_etc',
    day_of_week=0,
    hour=1,
    minute=0,
)

server.group(
    name='Create docker group',
    group='docker',
)

# if we are not running inside a docker container
if not host.get_fact(File, path='/.dockerenv'):

    # Cannot change hostname if running in a docker container
    server.hostname(
        name='Set the hostname',
        hostname='server1.example.com',
    )

    # Cannot change value on read-only filesystem
    # use "/sbin/sysctl -a | grep file-max" to check value
    server.sysctl(
        name='Change the fs.file-max value',
        key='fs.file-max',
        value='100000',
        persist=True,
    )

    if host.get_fact(LinuxName) in ['CentOS', 'RedHat']:
        server.modprobe(
            name='Silly example for modprobe',
            module='floppy',
        )

server.user(
    name='Ensure user is removed',
    user='kevin',
    present=False,
)

# multiple users
for user in ['kevin', 'bob']:
    server.user(
        name='Ensure user {} is removed'.format(user),
        user=user,
        present=False,
    )

server.group(
    name='Create uberadmin group',
    group='uberadmin',
)

# multiple groups
for group in ['wheel', 'lusers']:
    server.group(
        name='Create the group {}'.format(group),
        group=group,
    )

# To see output need to run pyinfra with '-v'
server.script(
    name='Hello',
    src='files/hello.bash',
)

# To see output need to run pyinfra with '-v'
some_var = 'blah blah blah '
server.script_template(
    name='Hello from script',
    src='templates/hello2.bash.j2',
    some_var=some_var,
)

# To see output need to run pyinfra with '-v'
server.shell(
    name='Say Hello',
    commands='echo Hello',
)
