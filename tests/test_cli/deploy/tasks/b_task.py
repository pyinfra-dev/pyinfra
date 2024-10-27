from pyinfra import host
from pyinfra.operations import server

server.shell(
    name=f"{host.data.get('keyword')} task operation",
    commands=f"echo {host.data.get('id')}",
)
