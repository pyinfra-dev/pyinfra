from pyinfra.operations import files, server

server.shell(commands=[], _sudo=True, _sudo_user="pyinfra")

files.line(path="path", line="line", _sudo=True)
