from pyinfra import host
from pyinfra.facts.server import LinuxName
from pyinfra.operations import apk, apt, files, git, yum

SUDO = True

if host.get_fact(LinuxName) in ['Alpine']:
    apk.packages(
        name='Install git',
        packages=['git'],
    )

if host.get_fact(LinuxName) in ['CentOS']:
    yum.packages(
        name='Install git',
        packages=['git'],
        update=True,
    )

if host.get_fact(LinuxName) in ['Ubuntu']:
    apt.packages(
        name='Install git',
        packages=['git'],
        update=True,
    )

src_dir = '/usr/local/src'
dest = src_dir + '/pyinfra'

files.directory(
    name='Ensure the src_dir directory exists',
    path=src_dir,
)

# Clone the pyinfra repo to do some pyinfra development
git.repo(
    name='Clone repo',
    src='https://github.com/Fizzadar/pyinfra.git',
    dest=dest,
    branch=None,  # use the default branch
)

git.config(
    name='Ensure user name is set for a repo',
    key='user.name',
    value='Anon E. Mouse',
    repo=dest,
)

git.config(
    name='Ensure email is set for a repo',
    key='user.email',
    value='anon@example.com',
    repo=dest,
)
