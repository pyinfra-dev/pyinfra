from pyinfra.operations import apt, npm

SUDO = True

apt.packages(
    {'Install node'},
    ['nodejs', 'npm'],
    update=True,
)

npm.packages(
    {'Install some npm packages'},
    ['react', 'express'],
)
