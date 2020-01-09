from pyinfra.modules import git

SUDO = True

# Clone the pyinfra repo to do some pyinfra development
dest = '/usr/local/src/pyinfra'
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
