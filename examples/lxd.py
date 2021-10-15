from pyinfra.operations import lxd, server


# Note: This is an example of running a command on remote
server.shell(
    name='Run lxd auto init',
    commands='lxd init --auto',
)

lxd.container(
    name='Add an ubuntu container',
    id='ubuntu19',
    image='ubuntu:19.10',
)
