from pyinfra.operations import apt, npm

SUDO = True

apt.packages(
    name='Install node',
    packages=['nodejs', 'npm'],
    update=True,
)

npm.packages(
    name='Install some npm packages',
    packages=['react', 'express'],
)
