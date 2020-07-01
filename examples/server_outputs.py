from pyinfra.operations import server

SUDO = True

# Various different outputs

# To see output need to run pyinfra with '-v'
a = server.script(
    name='Hello',
    src='files/hello.bash',
)
print('a', a)

# To see output need to run pyinfra with '-v'
b = server.shell(
    name='Say Hello',
    commands='echo Hello',
)
print('b', b)
