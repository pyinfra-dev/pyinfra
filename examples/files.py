from pyinfra import host
from pyinfra.facts.files import File
from pyinfra.facts.server import LinuxName
from pyinfra.operations import files

# Note: This requires files in the files/ directory.

SUDO = True

if host.get_fact(LinuxName) in ['CentOS', 'RedHat']:
    files.download(
        name='Download the Docker repo file',
        src='https://download.docker.com/linux/centos/docker-ce.repo',
        dest='/etc/yum.repos.d/docker-ce.repo',
    )

files.put(
    name='Update the message of the day file',
    src='files/motd',
    dest='/etc/motd',
    mode='644',
)

# prepare to do some maintenance
maintenance_line = 'SYSTEM IS DOWN FOR MAINTENANCE'
# files.line(
#     name='Add the down-for-maintenance line in /etc/motd',
#     '/etc/motd',
#     maintenance_line,
# )

# do some maintenance...
# Then, after the maintenance is done, remove the maintenance line
files.line(
    name='Remove the down-for-maintenance line in /etc/motd',
    path='/etc/motd',
    line=maintenance_line,
    replace='',
    present=False,
)

files.replace(
    name='Change part of a line in a file',
    path='/etc/motd',
    match='verboten',
    replace='forbidden',
)

# Sync local files/tempdir to remote /tmp/tempdir
files.sync(
    name='Sync a local directory with remote',
    src='files/tempdir',
    dest='/tmp/tempdir',
)

if host.get_fact(File, path='/etc/os-release'):
    files.get(
        name='Download a file from a remote',
        src='/etc/os-release',
        dest='/tmp/whocares',
    )

foo_variable = 'This is some foo variable contents'
files.template(
    name='Create a templated file',
    src='templates/foo.j2',
    dest='/tmp/foo',
    foo_variable=foo_variable,
)

files.link(
    name='Create link /etc/issue2 that points to /etc/issue',
    path='/etc/issue2',
    target='/etc/issue',
)

# Note: The directory /tmp/secret will get created with the default umask.
files.file(
    name='Create /tmp/secret/file',
    path='/tmp/secret/file',
    mode='600',
    user='root',
    group='root',
    touch=True,
    create_remote_dir=True,
)

files.directory(
    name='Ensure the /tmp/dir_that_we_want_removed is removed',
    path='/tmp/dir_that_we_want_removed',
    present=False,
)

# multiple directories
dirs = ['/tmp/aaa', '/tmp/bbb']
for dir in dirs:
    files.directory(
        name='Ensure the directory `{}` exists'.format(dir),
        path=dir,
    )
