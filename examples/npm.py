from pyinfra.operations import apt, npm


apt.packages(
    name='Install node',
    packages=['nodejs', 'npm'],
    update=True,
)

npm.packages(
    name='Install some npm packages',
    packages=['react', 'express'],
)
