from pyinfra import host
from pyinfra.modules import lxd

SUDO = True

# Note: This is an example of running a command on remote
server.shell(
    {'Run lxd auto init'},
    'lxd init --auto',
)

lxd.container(
    {'Add an ubuntu container'},
    'ubuntu19',
    image='ubuntu:19.10',
)
