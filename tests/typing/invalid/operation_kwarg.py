from pyinfra.operations import files, server

server.shell(commands=[], _invalid_kwarg=True)

files.line(path="path", line="line", _sudo=True, _invalid_kwarg=False)
