from pyinfra import host
from pyinfra.modules import files

# Note: This requires files in the files/ directory.

SUDO = True

if host.fact.linux_name in ['CentOS', 'RedHat']:
    files.download(
        {'Download the Docker repo file'},
        'https://download.docker.com/linux/centos/docker-ce.repo',
        '/etc/yum.repos.d/docker-ce.repo',
    )

files.put(
    {'Update the message of the day file'},
    'files/motd',
    '/etc/motd',
    mode='644',
)

# prepare to do some maintenance
maintenance_line = 'SYSTEM IS DOWN FOR MAINTENANCE'
# files.line(
#     {'Add the down-for-maintence line in /etc/motd'},
#     '/etc/motd',
#     maintenance_line,
# )

# do some maintenance...
# Then, after the mantenance is done, remove the maintenance line
files.line(
    {'Remove the down-for-maintenance line in /etc/motd'},
    '/etc/motd',
    maintenance_line,
    replace='',
    present=False,
)

files.replace(
    {'Change a value in a file'},
    '/etc/motd',
    'verboten',
    'forbidden',
)

# Sync local files/tempdir to remote /tmp/tempdir
files.sync(
    {'Sync a local directory with remote'},
    'files/tempdir',
    '/tmp/tempdir',
)

# TODO: not sure if bug or not
# files.get(
#     {'Download a file from a remote'},
#     '/etc/centos-release',
#     '/tmp/whocares',
# )

files.template(
    {'Create a templated file'},
    'templates/foo.j2',
    '/tmp/foo',
)

files.link(
    {'Create link /etc/issue2 that points to /etc/issue'},
    '/etc/issue2',
    '/etc/issue',
)

# Note: The directory /tmp/secret will get created with the default umask.
files.file(
    {'Create /tmp/secret/file'},
    '/tmp/secret/file',
    mode='600',
    user='root',
    group='root',
    touch=True,
    create_remote_dir=True,
)

files.directory(
    {'Ensure the /tmp/dir_that_we_want_removed is removed'},
    '/tmp/dir_that_we_want_removed',
    present=False,
)
