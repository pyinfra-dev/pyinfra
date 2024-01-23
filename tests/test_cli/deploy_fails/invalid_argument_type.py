from pyinfra.operations import server

server.shell(commands="uptime", _sudo=None)
