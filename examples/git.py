from pyinfra import host
from pyinfra.modules import apk, yum, apt, files, git

SUDO = True

if host.fact.linux_name in ['Alpine']:
    apk.packages(
        {'Install git'},
        'git',
    )

if host.fact.linux_name in ['CentOS']:
    yum.packages(
        {'Install git'},
        'git',
        update=True,
    )

if host.fact.linux_name in ['Ubuntu']:
    apt.packages(
        {'Install git'},
        'git',
        update=True,
    )

src_dir = '/usr/local/src'
dest = src_dir + '/pyinfra'

files.directory(
    {'Ensure the src_dir directory exists'},
    src_dir,
)

# Clone the pyinfra repo to do some pyinfra development
git.repo(
    {'Clone repo'},
    'https://github.com/Fizzadar/pyinfra.git',
    dest,
)

git.config(
    {'Ensure user name is set for a repo'},
    key='user.name',
    value='Anon E. Mouse',
    repo=dest,
)

git.config(
    {'Ensure email is set for a repo'},
    key='user.email',
    value='anon@example.com',
    repo=dest,
)
